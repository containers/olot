from pathlib import Path
import os
import datetime
import json
import argparse
from typing import List

from olot.oci.oci_image_manifest import create_oci_image_manifest, create_manifest_layers
from olot.oci.oci_common import Keys
from olot.utils.files import MIMETypes, tarball_from_file, targz_from_file
from olot.utils.types import compute_hash_of_str

def create_oci_artifact_from_model(source_dir: Path, dest_dir: Path):
    if not source_dir.exists():
        raise NotADirectoryError(f"Input directory '{source_dir}' does not exist.")

    if dest_dir is None:
        dest_dir = source_dir / "oci"
    os.makedirs(dest_dir, exist_ok=True)

    sha256_path = dest_dir / "blobs" / "sha256"
    os.makedirs(sha256_path, exist_ok=True)

    # assume flat structure for source_dir for now
    # TODO: handle subdirectories appropriately
    model_files = [source_dir / Path(f) for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]

    # Populate blobs directory
    layers = create_blobs(model_files, dest_dir)

    # Create the OCI image manifest
    manifest_layers = create_manifest_layers(model_files, layers)
    annotations = {
        Keys.image_created_annotation: datetime.datetime.now().isoformat()
    }
    artifactType = MIMETypes.mlmodel
    manifest = create_oci_image_manifest(
        artifactType=artifactType,
        layers=manifest_layers,
        annotations=annotations
    )
    manifest_json = json.dumps(manifest.dict(), indent=4, sort_keys=True)
    manifest_SHA = compute_hash_of_str(manifest_json)
    with open(sha256_path / manifest_SHA, "w") as f:
        f.write(manifest_json)


def create_blobs(model_files: List[Path], dest_dir: Path):
    """
    Create the blobs directory for an OCI artifact.
    """
    layers = {} # layer digest : (precomp, postcomp)
    sha256_path = dest_dir / "blobs" / "sha256"

    for model_file in model_files:
        file_name = os.path.basename(os.path.normpath(model_file))
        # handle model card file if encountered - assume README.md is the modelcard
        if file_name.endswith("README.md"):
            postcomp_chksum, precomp_chksum = targz_from_file(model_file, sha256_path)
            layers[file_name] = (precomp_chksum, postcomp_chksum)
        else:
            checksum = tarball_from_file(model_file, sha256_path)
            layers[file_name] = (checksum, "")
    return layers

# create a main function to test the function
def main():
    parser = argparse.ArgumentParser(description="Create OCI artifact from model")
    parser.add_argument('source_dir', type=str, help='Path to the source directory')
    args = parser.parse_args()

    source_dir = Path(args.source_dir)
    create_oci_artifact_from_model(source_dir, None)


