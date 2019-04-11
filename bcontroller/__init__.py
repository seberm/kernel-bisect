import sys
import subprocess
import os
import re
from logging import debug, info, warning


__author__ = "Otto Sabart"
__maintainer__ = "Otto Sabart"
__email__ = "seberm@seberm.com"
__version__ = "v0.0.1"

_DRY_RUN_ACTIVE = False
_CUR_DIR = os.path.dirname(os.path.realpath(__file__))

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

    return run_command([
        "ansible-playbook",
        "--limit",
        "duts",
        os.path.join(_CUR_DIR, "../playbooks/install-kernel.yml"),
        f"-e kernel_pkg_path={from_rpm} kernel_pkg={rpm_filename} reboot={reboot}",
    ])


def build(git_tree, make_opts, jobs, cc, rpmbuild_topdir):
    info("Current rpmbuild topdir: %s", rpmbuild_topdir)

    # Change OS environment only for the following command, not for whole
    # process
    modified_env = os.environ.copy()
    if cc:
        modified_env["CC"] = cc

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
        return run_command([
            "ansible",
            "-m",
            "ipmi_power",
            "-a",
            f"state=reset name={mgmt_host} user={mgmt_user} password={mgmt_password}",

            # Limit hosts
            "duts-mgmt"
        ])
    else:
        return run_command([
            "ansible",
            "-m",
            "reboot",
            "-a"
            "reboot_timeout=0",
        ])


def ping():
    return run_command([
        "ansible-playbook",
        "--limit",
        "duts",
        os.path.join(_CUR_DIR, "../playbooks/test.yml"),
    ])


def sh(command, args):
    return run_command([
        "ansible",
        "-m",
        "command",
        "-a",
        "%s %s" % (command, " ".join(args)),
        "duts",
    ])


def run(filename):
    abs_path_filename = os.path.abspath(filename)
    return run_command([
        "ansible-playbook",
        "--limit",
        "duts",
        os.path.join(_CUR_DIR, "../playbooks/run.yml"),
        f"-e filename={abs_path_filename}",
    ])


def bisect_start(git_tree, bad, good):
    return git(
        [
            "bisect",
            "start",
            bad,
        ] + list(good),
        work_dir=git_tree,
    )


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


def bisect_from_git(git_tree, filename, rpmbuild_topdir):
    """
    Kernel bisect algorithm.
    """

    p_out, p_build = build(git_tree, make_opts=[], jobs=4, cc="", rpmbuild_topdir=rpmbuild_topdir)
    if p_build.returncode != 0:
        return _BISECT_RET_SKIP

    # Grep this from make output and use this rpm path for package installation
    # Wrote: /tmp/bisect-my/RPMS/i386/kernel-5.1.0_rc3+-5.i386.rpm
    rpms = re.findall(r"^Wrote:\s+(?P<pkg_path>.*(?<!\.rpm)\.rpm)$", p_out, re.MULTILINE)

    # TODO: we must also check output and returncodes of ansible
    _, p_ans = kernel_install(from_rpm=rpms[0], reboot=True)
    if p_ans.returncode != 0:
        return _BISECT_RET_ABORT

    #uname_out = uname(["-r"])
    #json.loads(p_out)
    #check_booted_kernel using uname
    # -> same as old one? -> bisect_skip
    # -> booted into new one? -> continuing
    # exit_state = run(filename=filename)
    # -> propagate exit state into git-bisect
