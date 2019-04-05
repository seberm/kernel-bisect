import logging
import os
import sys
import subprocess
from logging import debug

import click


DEFAULT_LOGGING_MODE = "DEBUG"
__version__ = "v0.0.1"

PROGRAM_DESCRIPTION = """Some desc.\n"""
PROGRAM_EPILOG = ""

_CUR_DIR = os.path.dirname(os.path.realpath(__file__))


def run_command(args, stdout=subprocess.PIPE, stderr=None, env=None):
    debug("Running CMD: %s", args)
    process = subprocess.Popen(args, stdout=stdout, stderr=stderr, env=env)
    for c in iter(lambda: process.stdout.read(1), b''):
        sys.stdout.buffer.write(c)
        sys.stdout.flush()


@click.group()
@click.option(
    "-l",
    "--log",
    type=click.Choice(
        ["DEBUG", "WARNING", "INFO", "ERROR", "EXCEPTION"],
        case_sensitive=False),
    default=DEFAULT_LOGGING_MODE,
    show_default=True,
    help="Set logging level",
)
@click.version_option(version=__version__)
def cli(log):
    logging.basicConfig(level=log.upper())


@click.command(
    help="Install given kernel into DUT and reboot into it.",
)
@click.option(
    "--from-rpm",
    required=True,
    help="Path to RPM package to install on all DUTs.",
)
@click.option(
    "--reboot/--no-reboot",
    " /-R",
    default=True,
    help="Tell if system will be rebooted after the kernel installation.",
)
def kernel_install(from_rpm, reboot):
    rpm_filename = os.path.basename(from_rpm)

    # TODO: propagade reboot into ansible playbook?
    if reboot:
        raise NotImplementedError

    run_command([
        "ansible-playbook",
        "--limit",
        "duts",
        os.path.join(_CUR_DIR, "../playbooks/install-kernel.yml"),
        f"-e kernel_pkg_path={from_rpm} kernel_pkg={rpm_filename}",
    ])


@click.command(
    help="Build kernel inside its working directory",
)
@click.option(
    "-C",
    "--git-tree",
    default=_CUR_DIR,
    show_default=True,
    type=click.Path(exists=True),
    help="Path to the git working directory.",
)
@click.option(
    "-j",
    "--jobs",
    default=1,
    show_default=True,
    help="Specifies the number of jobs (commands) to run simultaneously.",
)
@click.option(
    "--cc",
    envvar="CC",
    help="Override current CC environment variable to specified value when compiling the kernel.",
)
def build(git_tree, jobs, cc):
    # Change OS environment only for the following command, not for whole
    # process
    modified_env = os.environ.copy()
    if cc:
        modified_env["CC"] = cc

    run_command(
        [
            "make",
            "-C",
            git_tree,
            "-j",
            str(jobs),
        ],
        env=modified_env,
    )


@click.command(
    help="Reboots all DUT machines.",
)
@click.option(
    "--use",
    type=click.Choice([
        # == Reboot over SSH
        "ansible",
        # == System reset without waiting for OS
        "ipmi",
        "amtc",

        # == Restart system using the Beaker - is it possible? TODO
        #"beaker",

        # "pdu",
    ]),
    default="ansible",
    show_default=True,
    help="Tells which way reboot the machine."
)
def reboot(use):
    # TODO: add support various methods of reboot

    if use == "ipmi":
        mgmt_host = ""  # TODO
        mgmt_user = "ADMIN"
        mgmt_password = "ADMIN"
        run_command([
            "ansible",
            "-m",
            "ipmi_power",
            "-a",
            f"state=reset name={mgmt_host} user={mgmt_user} password={mgmt_password}",

            # Limit hosts
            "mgmt"
        ])
    else:
        run_command([
            "ansible",
            "-m",
            "reboot",
            "-a"
            "reboot_timeout=0",
        ])


@click.command(
    help="Test connection to DUTs.",
)
def ping():
    run_command([
        "ansible-playbook",
        "--limit",
        "duts",
        os.path.join(_CUR_DIR, "../playbooks/test.yml"),
    ])


@click.command(
    help="Copy and run file specified by FILENAME on DUTs. Print stdout and stderr onto standard outputs. This program exit code will be the same as the remote process exit code.",
)
@click.argument(
    "filename",
    type=click.Path(exists=True),
)
def run(filename):
    abs_path_filename = os.path.abspath(filename)
    run_command([
        "ansible-playbook",
        "--limit",
        "duts",
        os.path.join(_CUR_DIR, "../playbooks/run.yml"),
        f"-e filename={abs_path_filename}",
    ])


@click.group(
    help="Control kernel bisect. This is basically a wrapper around git-bisect.",
)
@click.option(
    "-C",
    "--git-tree",
    default=_CUR_DIR,
    show_default=True,
    type=click.Path(exists=True),
    help="Path to the git working directory.",
)
def bisect(git_tree):
    pass


@click.command(
    name="start",
    help="Start git bisect.",
)
@click.argument(
    "bad",
    required=False,
)
@click.argument(
    "good",
    nargs=-1,
)
def bisect_start(bad, good):
    pass


@click.command(
    name="run",
    help="Automatically run git bisect using a script (given by FILENAME) which can tell if the current source code is good or bad",
)
@click.argument(
    "filename",
    type=click.Path(exists=True),
)
def bisect_run(filename):
    pass


@click.command(
    name="good",
    help="Mark current revision as GOOD.",
)
@click.argument(
    "revs",
    nargs=-1,
)
def bisect_good(revs):
    pass


@click.command(
    name="bad",
    help="Mark current revision as BAD.",
)
@click.argument(
    "revs",
    nargs=-1,
)
def bisect_bad(revs):
    pass


@click.command(
    name="skip",
    help="Skip current revision. Try another one.",
)
def bisect_skip():
    pass


cli.add_command(ping)
cli.add_command(build)
cli.add_command(kernel_install)
cli.add_command(reboot)
cli.add_command(run)

bisect.add_command(bisect_start)
bisect.add_command(bisect_run)
bisect.add_command(bisect_good)
bisect.add_command(bisect_bad)
bisect.add_command(bisect_skip)
cli.add_command(bisect)
