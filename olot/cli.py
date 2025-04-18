from os import PathLike
import click
import logging

from .basics import RemoveOriginals, oci_layers_on_top


@click.command()
@click.option("-m", "--modelcard", type=click.Path(exists=True, file_okay=True, dir_okay=False))
@click.argument('ocilayout', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('model_files', nargs=-1)
@click.option('-r', '--remove-originals', type=click.Choice([e.value for e in RemoveOriginals], case_sensitive=False), is_flag=False, flag_value=RemoveOriginals.DEFAULT)
def cli(ocilayout: str, modelcard: PathLike, model_files, remove_originals: bool):
    logging.basicConfig(level=logging.INFO)
    oci_layers_on_top(ocilayout, model_files, modelcard, remove_originals=RemoveOriginals(remove_originals) if remove_originals else None)
