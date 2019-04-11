import sys
import subprocess
import os
from logging import debug, info, warning


__author__ = "Otto Sabart"
__maintainer__ = "Otto Sabart"
__email__ = "seberm@seberm.com"
__version__ = "v0.0.1"

_DRY_RUN_ACTIVE = False
_CUR_DIR = os.path.dirname(os.path.realpath(__file__))


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
