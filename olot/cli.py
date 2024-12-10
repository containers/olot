from pathlib import Path
import click



from .basics import oci_layers_on_top


@click.command()
@click.argument('ocilayout', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.argument('model_files', nargs=-1)
def cli(ocilayout: str, model_files):
    oci_layers_on_top(Path(ocilayout), model_files)
