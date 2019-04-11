import logging
import os
import tempfile
import re
from logging import warning, info

import click

# TODO: Ansible output parser...
# TODO: propagate exit state of remote script to git-bisect run sh -c "exit N"

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

# 0 -> good
# 1 <= N <= 127 (except 125) -> bad
# 127> -> aborts bisect
# 125 -> skip
_BISECT_RET_GOOD = 0
_BISECT_RET_BAD = 1
_BISECT_RET_SKIP = 125
_BISECT_RET_ABORT = 128


def dry(fnc, *args, **kwargs):
    if _DRY_RUN_ACTIVE:
        warning("DRY-RUN: not calling: %s(%s, %s)", fnc.__name__, args, kwargs)
        return

    return fnc(*args, **kwargs)


@click.group()
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
@click.version_option(version=__version__)
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
    help="Build kernel inside its working directory",
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
    default=1,
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
def build(git_tree, make_opts, jobs, cc, rpmbuild_topdir):
    dry(bcontroller.build, git_tree, make_opts, jobs, cc, rpmbuild_topdir)


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
    default="",
    required=False,
)
@click.argument(
    "good",
    nargs=-1,
    required=False,
)
@click.pass_context
def bisect_start(ctx, bad, good):
    raise NotImplementedError
#    git(
#        [
#            "bisect",
#            "start",
#            bad,
#        ] + list(good),
#        work_dir=ctx.obj["git_tree"],
#    )


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
    raise NotImplementedError
    #git(
    #    [
    #        "bisect",
    #        "good",
    #    ] + list(revs),
    #    work_dir=ctx.obj["git_tree"],
    #)


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
    raise NotImplementedError
    #git(
    #    [
    #        "bisect",
    #        "bad",
    #    ] + list(revs),
    #    work_dir=ctx.obj["git_tree"],
    #)


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
    raise NotImplementedError
    #git(
    #    [
    #        "bisect",
    #        "skip",
    #    ] + list(revs),
    #    work_dir=ctx.obj["git_tree"],
    #)


@click.command(
    name="log",
    help="Show bisect log.",
)
@click.pass_context
def bisect_log(ctx):
    raise NotImplementedError
    #git(
    #    [
    #        "bisect",
    #        "log",
    #    ],
    #    work_dir=ctx.obj["git_tree"],
    #)


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

    p_out, p_build = bcontroller.build(git_tree, make_opts=[], jobs=4, cc="", rpmbuild_topdir=DEFAULT_RPMBUILD_TOPDIR)
    if p_build.returncode != 0:
        return _BISECT_RET_SKIP

    # Grep this from make output and use this rpm path for package installation
    # Wrote: /tmp/bisect-my/RPMS/i386/kernel-5.1.0_rc3+-5.i386.rpm
    rpms = re.findall(r"^Wrote:\s+(?P<pkg_path>.*(?<!\.rpm)\.rpm)$", p_out, re.MULTILINE)

    # TODO: we must also check output and returncodes of ansible
    _, p_ans = bcontroller.kernel_install(from_rpm=rpms[0], reboot=True)
    if p_ans.returncode != 0:
        return _BISECT_RET_ABORT

    #uname_out = uname(["-r"])
    #json.loads(p_out)
    #check_booted_kernel using uname
    # -> same as old one? -> bisect_skip
    # -> booted into new one? -> continuing
    # exit_state = run(filename=filename)
    # -> propagate exit state into git-bisect



cli.add_command(ping)
cli.add_command(build)
cli.add_command(kernel_install)
cli.add_command(uname)
cli.add_command(reboot)
cli.add_command(run)
cli.add_command(sh)

#bisect.add_command(bisect_start)
#bisect.add_command(bisect_run)
#bisect.add_command(bisect_good)
#bisect.add_command(bisect_bad)
#bisect.add_command(bisect_skip)
#bisect.add_command(bisect_log)
bisect.add_command(bisect_from_git)
cli.add_command(bisect)
