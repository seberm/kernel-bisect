import sys
import subprocess
import os
import re
import json
import multiprocessing
from logging import debug, info, warning


__author__ = "Otto Sabart"
__maintainer__ = "Otto Sabart"
__email__ = "seberm@seberm.com"
__version__ = "v0.0.1"

_DRY_RUN_ACTIVE = False
_CUR_DIR = os.path.dirname(os.path.realpath(__file__))

os.environ["ANSIBLE_CONFIG"] = os.path.join(_CUR_DIR, "../ansible.cfg")

# 0 -> good
# 1 <= N <= 127 (except 125) -> bad
# 127> -> aborts bisect
# 125 -> skip
_BISECT_RET_GOOD = 0
_BISECT_RET_BAD = 1
_BISECT_RET_SKIP = 125
_BISECT_RET_ABORT = 128


class BControlError(Exception):
    pass


def run_command(args, stdout=subprocess.PIPE, stderr=None, env=None):
    debug("Running CMD: %s", args)
    process = subprocess.Popen(args, stdout=stdout, stderr=stderr, env=env)
    out = []
    for c in iter(lambda: process.stdout.read(1), b''):
        sys.stdout.buffer.write(c)
        sys.stdout.flush()
        out.append(c.decode('utf-8'))

    process.communicate()
    output = ''.join(out)

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

    return run_command(ansible_cmd)


def ansible_playbook(playbook, limit, **argv):
    params = " ".join(
        f"{key}={val}" for key, val in argv.items()
    )

    if params:
        params = f"--extra-vars {params}"

    ansible_playbook_cmd = [
        "ansible-playbook",
        "--limit",
        limit,
        playbook,
    ]

    if params:
        ansible_playbook_cmd.append(params)

    return run_command(ansible_playbook_cmd)


# TODO: support multiple rpms?
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
            "oldconfig",
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
    Kernel bisect algorithm.
    """
    p_out, p_build = build(git_tree, make_opts=[], jobs=multiprocessing.cpu_count(), cc="", rpmbuild_topdir=rpmbuild_topdir, oldconfig=True)
    if p_build.returncode != 0:
        return _BISECT_RET_SKIP

    # Grep this from make output and use this rpm path for package installation
    # Wrote: /tmp/bisect-my/RPMS/i386/kernel-5.1.0_rc3+-5.i386.rpm
    rpms = re.findall(r"^Wrote:\s+(?P<pkg_path>.*(?<!\.rpm)\.rpm)$", p_out, re.MULTILINE)

    # TODO: we must also check output and returncodes of ansible
    _, p_ans = kernel_install(from_rpm=rpms[0], reboot=True)
    if p_ans.returncode != 0:
        return _BISECT_RET_ABORT

    # Retrieve kernel version from filename
    m_groups = re.match(r"^kernel-(?P<kernel_version>.*(?<!\.rpm))\.rpm$", os.path.basename(rpms[0]))
    built_kernel_version = m_groups.group("kernel_version")
    if not check_installed_kernel(must_match_kernel=built_kernel_version):
        # Kernel did not boot correctly - panic?
        return _BISECT_RET_SKIP

    _, p_run = run(filename)
    return p_run.returncode


def check_installed_kernel(must_match_kernel):
    debug("check-installed-kernel: must match: %s", must_match_kernel)
    # Check if the booted kernel matches the built kernel
    uname_ans_out, p_uname = sh("uname", ["-r"])
    if p_uname.returncode != 0:
        return _BISECT_RET_ABORT

    uname_ans_d = json.loads(uname_ans_out)
    duts = uname_ans_d["plays"][0]["tasks"][0]["hosts"]

    for host, val in duts.items():
        uname_kernel_ver = val["stdout"]
        debug("check-installed-kernel: %s: %s", host, uname_kernel_ver)
        if must_match_kernel != uname_kernel_ver:
            return False

    return True
