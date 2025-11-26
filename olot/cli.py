from os import PathLike
import click
import logging

from .basics import RemoveOriginals, oci_layers_on_top


@click.command()
@click.option("-m", "--modelcard", type=click.Path(exists=True, file_okay=True, dir_okay=False), help="file to be used for ModelCarD; if provided, make sure it's not part of [MODEL_FILES] arguments to avoid redundancies.")
@click.option("--add-modelpack", is_flag=True)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output (DEBUG level logging)")
@click.argument('ocilayout', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('model_files', nargs=-1)
@click.option('-r', '--remove-originals', type=click.Choice([e.value for e in RemoveOriginals], case_sensitive=False), is_flag=False, flag_value=RemoveOriginals.DEFAULT)
def cli(ocilayout: str, modelcard: PathLike, model_files, remove_originals: bool, add_modelpack: bool, verbose: bool):
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    oci_layers_on_top(ocilayout, model_files, modelcard, remove_originals=RemoveOriginals(remove_originals) if remove_originals else None, add_modelpack=add_modelpack)
