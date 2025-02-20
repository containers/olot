from os import PathLike
import click
import logging

from .basics import oci_layers_on_top


@click.command()
@click.option("-m", "--modelcard", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.argument('ocilayout', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('model_files', nargs=-1)
@click.option('-r', '--remove-originals', is_flag=True)
def cli(ocilayout: str, modelcard: PathLike, model_files, remove_originals: bool):
    logging.basicConfig(level=logging.INFO)
    oci_layers_on_top(ocilayout, model_files, modelcard, remove_originals=remove_originals)
