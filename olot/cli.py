from os import PathLike
from pathlib import Path
import click
import logging

from .basics import oci_layers_on_top


@click.command()
@click.option("-m", "--modelcard", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.argument('ocilayout', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('model_files', nargs=-1)
def cli(ocilayout: str, modelcard: PathLike, model_files):
    logging.basicConfig(level=logging.INFO)
    oci_layers_on_top(ocilayout, model_files, modelcard)
