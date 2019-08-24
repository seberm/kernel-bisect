import sys
import subprocess
import os
import re
import json
import multiprocessing
import logging
from logging import debug, info, warning

import click

from ._version import get_versions
v = get_versions()
__version__ = v.get("closest-tag", v["version"])
del get_versions, v


__author__ = "Otto Sabart"
__maintainer__ = __author__
__email__ = "seberm@seberm.com"

_DRY_RUN_ACTIVE = False
_CUR_DIR = os.path.dirname(os.path.realpath(__file__))

os.environ["ANSIBLE_CONFIG"] = os.path.join(_CUR_DIR, "../ansible.cfg")


class BControlError(click.ClickException):
    pass


class BControlCommandError(BControlError):
    def __init__(self, args, process, output, stderr_output):
        super().__init__("Program [$ %s] exited with non-zero exit state (%d).\n\nOutput:\n%s\n\n Stderr output:\n%s" % (" ".join(args), process.returncode, output, stderr_output))
        self.__dict__.update(locals())


class BControlBisect(Exception):
    """
    Abstract bisect exception.
    """
    pass


class BControlBisectSkip(BControlBisect):
    pass


class BControlBisectAbort(BControlBisect):
    pass


def convert_json(json_input):
    return json.loads(json_input)


def run_command(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=None):
    debug("Running CMD: %s", args)
    process = subprocess.Popen(args, stdout=stdout, stderr=stderr, env=env)
    out = []
    for c in iter(lambda: process.stdout.read(1), b''):
        if logging.root.level == logging.DEBUG:
            sys.stdout.buffer.write(c)

        sys.stdout.flush()
        out.append(c.decode('utf-8'))

    _, stderr_output = process.communicate()
    output = ''.join(out)

    if process.returncode != 0:
        raise BControlCommandError(
            args,
            process,
            output,
            stderr_output.decode("utf-8"),
        )

    return output, process


def git(args, work_dir=os.getcwd()):
    cmd_args = [
        "git",
        "-C",
        work_dir,
    ] + args

    return run_command(cmd_args)


def ansible(module_name, limit, params=""):
    ansible_cmd = [
        "ansible",
        "-m",
        module_name,
    ]

    if params:
        ansible_cmd += [
            "--args",
            params,
        ]

    # Limit hosts
    ansible_cmd.append(limit)

    try:
        return run_command(ansible_cmd)
    except BControlCommandError as e:
        # Parse ansible JSON output to get error message
        ans_out = convert_json(e.output)
        raise BControlError(ans_out["stats"])


def ansible_playbook(playbook, limit, **argv):
    extra_vars = " ".join(
        f"{key}={val}" for key, val in argv.items()
    )

    ansible_playbook_cmd = [
        "ansible-playbook",
        "--limit",
        limit,
        playbook,
    ]

    if extra_vars:
        ansible_playbook_cmd.append("--extra-vars")
        ansible_playbook_cmd.append(extra_vars)

    try:
        return run_command(ansible_playbook_cmd)
    except BControlCommandError as e:
        # Parse ansible JSON output to get error message
        ans_out = convert_json(e.output)
        raise BControlError(ans_out["stats"])


# TODO: support multiple rpms? (kernel-headers?)
def kernel_install(from_rpm, reboot):
    """
    Install given kernel to the target system(s) and try to boot into it. This
    command *does not* check if system(s) successfully booted into the given
    kernel.
    """
    rpm_filename = os.path.basename(from_rpm)

    if not reboot:
        warning("kernel-install: not rebooting the kernel, option -R/--no-reboot is active.")

    debug("kernel-install: installing new kernel using ansible")
    return ansible_playbook(
        os.path.join(_CUR_DIR, "../playbooks/install-kernel.yml"),
        "duts",
        kernel_pkg_path=from_rpm,
        kernel_pkg=rpm_filename,
        reboot=reboot,
    )


# TODO: what about kernel config? we should stop if there is no config...or run
# make olddefconfig?
def build(git_tree, make_opts, jobs, cc, rpmbuild_topdir, oldconfig):
    info("Current rpmbuild topdir: %s", rpmbuild_topdir)

    # Change OS environment only for the following command, not for whole
    # process
    modified_env = os.environ.copy()
    if cc:
        modified_env["CC"] = cc

    if oldconfig:
        config_cmd = [
            "make",
            "-C",
            git_tree,

            # Makefile target
            "oldconfig",  # or use olddefconfig?
        ]
        run_command(config_cmd, env=modified_env)

    build_cmd = [
        "make",
        "-C",
        git_tree,
        "-j",
        str(jobs),

        # Makefile target
        "binrpm-pkg",

        # Build packages in well-known directory
        f'RPMOPTS=--define \"_topdir {rpmbuild_topdir}\"',
    ]

    if make_opts:
        build_cmd.extend(make_opts.split(" "))

    return run_command(build_cmd, env=modified_env)


def reboot(use):
    # TODO: add support various methods of reboot

    if use == "ipmi":
        mgmt_host = ""  # TODO
        mgmt_user = "USERID"
        mgmt_password = "PASSW0RD"
        return ansible(
            "ipmi_power",
            "duts-mgmt",
            state="reset",
            name=mgmt_host,
            user=mgmt_user,
            password=mgmt_password,
        )
    else:
        return ansible(
            "reboot",
            "duts",
            reboot_timeout=0,
        )


def ping():
    return ansible_playbook(
        os.path.join(_CUR_DIR, "../playbooks/test.yml"),
        "duts",
    )


def sh(command, args):
    return ansible(
        "command",
        "duts",
        "%s %s" % (command, " ".join(args)),
    )


def run(filename):
    abs_path_filename = os.path.abspath(filename)
    return ansible_playbook(
        os.path.join(_CUR_DIR, "../playbooks/run.yml"),
        "duts",
        filename=abs_path_filename,
    )


def bisect_start(git_tree, bad, good):
    start_cmd = [
        "bisect",
        "start",
    ]

    if bad is not None:
        start_cmd.append(bad)

    start_cmd += list(good)
    return git(start_cmd, work_dir=git_tree)


def bisect_good(git_tree, revs):
    return git(
        [
            "bisect",
            "good",
        ] + list(revs),
        work_dir=git_tree,
    )


def bisect_bad(git_tree, revs):
    return git(
        [
            "bisect",
            "bad",
        ] + list(revs),
        work_dir=git_tree,
    )


def bisect_skip(git_tree, revs):
    return git(
        [
            "bisect",
            "skip",
        ] + list(revs),
        work_dir=git_tree,
    )


def bisect_log(git_tree):
    return git(
        [
            "bisect",
            "log",
        ],
        work_dir=git_tree,
    )


def bisect_reset(git_tree):
    return git(
        [
            "bisect",
            "reset",
        ],
        work_dir=git_tree,
    )


def bisect_from_git(git_tree, filename, rpmbuild_topdir):
    """
    Kernel bisect algorithm for $ git bisect run %prog from-git.
    """
    try:
        p_out, p_build = build(
            git_tree,
            make_opts=[],
            jobs=multiprocessing.cpu_count(),
            cc="",
            rpmbuild_topdir=rpmbuild_topdir,
            oldconfig=True,
        )
    except BControlCommandError:
        raise BControlBisectSkip

    # Grep this from make output and use this rpm path for package installation
    # Wrote: /tmp/bisect-my/RPMS/i386/kernel-5.1.0_rc3+-5.i386.rpm
    rpms = re.findall(r"^Wrote:\s+(?P<pkg_path>.*(?<!\.rpm)\.rpm)$", p_out, re.MULTILINE)

    # TODO: we must also check output and returncodes of ansible
    try:
        #_, p_ans = kernel_install(from_rpm=rpms[0], reboot=True)
        _, p_ans = kernel_install(from_rpm=rpms[0], reboot=False)
    except BControlCommandError:
        raise BControlBisectAbort

    # Retrieve kernel version from filename
    m_groups = re.match(r"^kernel-(?P<kernel_version>.*(?<!\.rpm))\.rpm$", os.path.basename(rpms[0]))
    built_kernel_version = m_groups.group("kernel_version")
    if not check_installed_kernel(must_match_kernel=built_kernel_version):
        # Kernel did not boot correctly - panic?
        raise BControlBisectSkip

    try:
        _, p_run = run(filename)
    except BControlCommandError as e:
        return e.process.returncode
    else:
        return p_run.returncode


def check_installed_kernel(must_match_kernel):
    """
    Check if the booted kernel matches the built kernel.
    """
    debug("check-installed-kernel: must match: %s", must_match_kernel)
    try:
        uname_ans_out, p_uname = sh("uname", ["-r"])
    except BControlCommandError:
        return False

    uname_ans_d = convert_json(uname_ans_out)
    duts = uname_ans_d["plays"][0]["tasks"][0]["hosts"]

    for host, val in duts.items():
        uname_kernel_ver = val["stdout"]
        debug("check-installed-kernel: %s: %s", host, uname_kernel_ver)
        if must_match_kernel != uname_kernel_ver:
            return False

    return True
