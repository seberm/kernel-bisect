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


def run_command(args, stdout=subprocess.PIPE, stderr=None):
    debug("Running CMD: %s", args)
    process = subprocess.Popen(args, stdout=stdout, stderr=stderr, check=True, universal_newlines=True)
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
def kernel_install(from_rpm):
    rpm_filename = os.path.basename(from_rpm)

    run_command([
        "ansible-playbook",
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
    help="Sets the CC nevironment variable to specified value when compiling the kernel.",
)
def build(git_tree, jobs, cc):
    # TODO: CC
    run_command([
        "make",
        "-C",
        git_tree,
        "-j",
        jobs,
    ])


@click.command(
    help="Reboots all DUT machines.",
)
@click.option(
    "--use",
    type=click.Choice([
        # == Reboot over SSH
        "ansible",
        "ipmi",
        "amtc",
        # "pdu",
    ]),
    default="ansible",
    show_default=True,
    help="Tells which way reboot the machine."
)
def reboot(use):
    run_command([
        "ansible",
        "-m",
        "reboot",
        "-a"
        "reboot_timeout=0",
    ])


@click.command(
    help="Tells which way reboot the machine.",
)
def ping():
    run_command([
        "ansible-playbook",
        os.path.join(_CUR_DIR, "../playbooks/test.yml"),
    ])


cli.add_command(ping)
cli.add_command(build)
cli.add_command(kernel_install)
cli.add_command(reboot)
