import logging
import os
import sys
import multiprocessing
import tempfile
from logging import warning, info

import click

from bcontroller import __version__
import bcontroller


DEFAULT_LOGGING_MODE = "DEBUG"
DEFAULT_RPMBUILD_TOPDIR = os.path.join(
    tempfile.gettempdir(),
    "rpmbuild-kernel-bisect",
)

PROGRAM_DESCRIPTION = "Some text."
PROGRAM_EPILOG = ""

_CUR_DIR = os.path.dirname(os.path.realpath(__file__))


def dry(fnc, *args, **kwargs):
    if _DRY_RUN_ACTIVE:
        warning("DRY-RUN: not calling: %s(%s, %s)", fnc.__name__, args, kwargs)
        return

    return fnc(*args, **kwargs)


@click.group(
    epilog=PROGRAM_EPILOG,
    context_settings={
        'help_option_names': [
            '-h',
            '--help',
        ]
    }
)
@click.option(
    "-l",
    "--log",
    type=click.Choice(
        ["DEBUG", "WARNING", "INFO", "ERROR", "EXCEPTION"],
        case_sensitive=False,
    ),
    default=DEFAULT_LOGGING_MODE,
    show_default=True,
    help="Set logging level.",
)
@click.version_option(version="v%s" % __version__)
@click.option(
    "-n",
    "--dry-run",
    default=False,
    is_flag=True,
    help="Do not launch any action, just print it out.",
)
@click.pass_context
def cli(ctx, log, dry_run):
    """
    Script for automatic kernel bisection.
    """
    if ctx.obj is None:
        ctx.obj = {}

    logging.basicConfig(level=log.upper())

    global _DRY_RUN_ACTIVE
    _DRY_RUN_ACTIVE = dry_run

    if _DRY_RUN_ACTIVE:
        warning("DRY-RUN mode active!")


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
    dry(bcontroller.kernel_install, from_rpm, reboot)


@click.command(
    help="Return current kernel information. If you want to provide arguments for uname, just separate them with double commans (e.g. $ %(prog)s uname -- --all)."
)
@click.argument(
    "args",
    nargs=-1,
    # TODO: --all shoud be default for this option!
    #default=["--all"],
)
def uname(args):
    bcontroller.sh("uname", args)


@click.command(
    help="Build kernel inside its working directory.",
)
@click.option(
    "-C",
    "--git-tree",
    default=os.getcwd(),
    show_default=True,
    type=click.Path(exists=True),
    help="Path to the git working directory.",
)
@click.option(
    "-m",
    "--make-opts",
    help="Append more options to MAKE command.",
)
@click.option(
    "-j",
    "--jobs",
    default=multiprocessing.cpu_count(),
    show_default=True,
    help="Specifies the number of jobs (commands) to run simultaneously.",
)
@click.option(
    "--cc",
    envvar="CC",
    help="Override current CC environment variable to specified value when compiling the kernel.",
)
@click.option(
    "--rpmbuild-topdir",
    default=DEFAULT_RPMBUILD_TOPDIR,
    show_default=True,
    help="Sets the rpmbuild _topdir variable. It is a place where rpmbuild create all RPM related files (spec file, SRPM, sources, etc.).",
)
@click.option(
    "--oldconfig",
    default=True,
    is_flag=True,
    show_default=True,
    help="Try to regenerate kernel configuration file using the `make oldconfig`.",
)
def build(git_tree, make_opts, jobs, cc, rpmbuild_topdir, oldconfig):
    dry(bcontroller.build, git_tree, make_opts, jobs, cc, rpmbuild_topdir, oldconfig)


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
    dry(bcontroller.reboot, use)


@click.command(
    help="Test connection to DUTs.",
)
def ping():
    dry(bcontroller.ping)



@click.command(
    help="Run specified command on all DUTs.",
)
@click.argument(
    "command",
    required=True,
)
@click.argument(
    "args",
    nargs=-1,
)
def sh(command, args):
    dry(bcontroller.sh, command, args)


@click.command(
    help="Copy and run file specified by FILENAME on DUTs. Print stdout and stderr onto standard outputs. This program exit code will be the same as the remote process exit code.",
)
@click.argument(
    "filename",
    type=click.Path(exists=True),
)
def run(filename):
    dry(run, filename)


@click.group(
    help="Control kernel bisect. This is basically a wrapper around git-bisect.",
)
@click.option(
    "-C",
    "--git-tree",
    default=os.getcwd(),
    show_default=True,
    type=click.Path(exists=True),
    help="Path to the git working directory.",
)
@click.pass_context
def bisect(ctx, git_tree):
    if ctx.obj is None:
        ctx.obj = {}

    info("Current git working directory: %s", git_tree)
    ctx.obj["git_tree"] = git_tree


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
    required=False,
)
@click.pass_context
def bisect_start(ctx, bad, good):
    dry(bcontroller.bisect_start, ctx.obj["git_tree"], bad, good)


@click.command(
    name="run",
    help="Automatically run git bisect using a script (given by FILENAME) which can tell if the current source code is good or bad",
)
@click.argument(
    "filename",
    type=click.Path(exists=True),
)
@click.pass_context
# TODO: support CC option?
def bisect_run(ctx, filename):
    """
    Note that the script (my_script in the above example) should exit with code
    0 if the current source code is good/old, and exit with a code between 1
    and 127 (inclusive), except 125, if the current source code is bad/new.
    """
    raise NotImplementedError

    # TODO: run `git bisect run <bcontrol bisect-from-git` as a subprocess
    #git_tree = ctx.obj["git_tree"]


@click.command(
    name="good",
    help="Mark current revision as GOOD.",
)
@click.argument(
    "revs",
    nargs=-1,
)
@click.pass_context
def bisect_good(ctx, revs):
    dry(bcontroller.bisect_good, ctx.obj["git_tree"], revs)


@click.command(
    name="bad",
    help="Mark current revision as BAD.",
)
@click.argument(
    "revs",
    nargs=-1,
)
@click.pass_context
def bisect_bad(ctx, revs):
    dry(bcontroller.bisect_bad, ctx.obj["git_tree"], revs)


@click.command(
    name="skip",
    help="Skip current revision. Try another one.",
)
@click.argument(
    "revs",
    nargs=-1,
)
@click.pass_context
def bisect_skip(ctx, revs):
    dry(bcontroller.bisect_skip, ctx.obj["git_tree"], revs)


@click.command(
    name="log",
    help="Show bisect log.",
)
@click.pass_context
def bisect_log(ctx):
    dry(bcontroller.bisect_log, ctx.obj["git_tree"])


@click.command(
    name="reset",
    help="Reset the bisect.",
)
@click.pass_context
def bisect_reset(ctx):
    dry(bcontroller.bisect_reset, ctx.obj["git_tree"])


@click.command(
    name="from-git",
    help="Use this sub-command when running `git bisect run` directly.",
)
@click.argument(
    "filename",
    type=click.Path(exists=True),
)
@click.pass_context
def bisect_from_git(ctx, filename):
    """
    Kernel bisect algorithm.
    """
    git_tree = ctx.obj["git_tree"]
    sys.exit(bcontroller.bisect_from_git(git_tree, filename, DEFAULT_RPMBUILD_TOPDIR))


cli.add_command(ping)
cli.add_command(build)
cli.add_command(kernel_install)
cli.add_command(uname)
cli.add_command(reboot)
cli.add_command(run)
cli.add_command(sh)

bisect.add_command(bisect_start)
bisect.add_command(bisect_run)
bisect.add_command(bisect_good)
bisect.add_command(bisect_bad)
bisect.add_command(bisect_skip)
bisect.add_command(bisect_log)
bisect.add_command(bisect_reset)
bisect.add_command(bisect_from_git)
cli.add_command(bisect)
