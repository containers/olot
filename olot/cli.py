import logging
from os import PathLike

import click

from .basics import RemoveOriginals, oci_layers_on_top


@click.command()
@click.option("-m", "--modelcard", type=click.Path(exists=True, file_okay=True, dir_okay=False), help="file to be used for ModelCarD; if provided, make sure it's not part of [MODEL_FILES] arguments to avoid redundancies.")
@click.option("--add-modelpack", is_flag=True)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output (DEBUG level logging)")
@click.option("--root-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True), default=None, help="root directory of the model files. When provided, each file's path relative to ROOT_DIR is used to preserve its subdirectory structure inside the OCI layer (e.g. a file at ROOT_DIR/onnx/model.onnx is stored as /models/onnx/model.onnx). Without it, only the file's basename is used, so files with the same name in different subdirectories will collide and overwrite each other.")
@click.argument('ocilayout', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('model_files', nargs=-1)
@click.option('-r', '--remove-originals', type=click.Choice([e.value for e in RemoveOriginals], case_sensitive=False), is_flag=False, flag_value=RemoveOriginals.DEFAULT)
def cli(ocilayout: str, modelcard: PathLike, model_files, remove_originals: bool, add_modelpack: bool, verbose: bool, root_dir: PathLike):
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
    oci_layers_on_top(ocilayout, model_files, modelcard, root_dir=root_dir, remove_originals=RemoveOriginals(remove_originals) if remove_originals else None, add_modelpack=add_modelpack)
