import logging
from logging import error

import click

from bcontroller import BControlError


DEFAULT_LOGGING_MODE = "WARNING"
__version__ = "v0.0.1"

PROGRAM_DESCRIPTION = """Some desc.\n"""
PROGRAM_EPILOG = ""


@click.group()
@click.option("-l", "--log",type=click.Choice(["DEBUG", "WARNING", "INFO", "ERROR", "EXCEPTION"], case_sensitive=False), default=DEFAULT_LOGGING_MODE, help="Set logging level")
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, log, version):
    logging.basicConfig(level=log.upper())

    try:
        pass
    except BControlError as e:
        error(e)
        return 99

    return 0


#@click.command()
#@click.option("--some", required=True, help="some")
#def test(some):
#    click.echo("Ahoj")
#
#cli.add_command(test)

#def main():
