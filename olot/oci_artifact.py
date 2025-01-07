from pathlib import Path
import os
import json
import argparse
from typing import List

from olot.oci.oci_image_manifest import create_oci_image_manifest, create_manifest_layers
from olot.oci.oci_image_layout import create_ocilayout
from olot.oci.oci_common import MediaTypes, Values
from olot.oci.oci_image_index import Manifest, create_oci_image_index
from olot.utils.files import MIMETypes, tarball_from_file, targz_from_file
from olot.utils.types import compute_hash_of_str

def create_oci_artifact_from_model(source_dir: Path, dest_dir: Path):
    """
    Create an OCI artifact from a model directory.

    Args:
        source_dir: The directory containing the model files.
        dest_dir: The directory to write the OCI artifact to. If None, a directory named 'oci' will be created in the source directory.
    """
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
    artifactType = MIMETypes.mlmodel
    manifest = create_oci_image_manifest(
        artifactType=artifactType,
        layers=manifest_layers,
    )
    manifest_json = json.dumps(manifest.dict(exclude_none=True), indent=4, sort_keys=True)
    manifest_SHA = compute_hash_of_str(manifest_json)
    with open(sha256_path / manifest_SHA, "w") as f:
        f.write(manifest_json)

    # Create the OCI image index
    index = create_oci_image_index(
        manifests = [
            Manifest(
                mediaType=MediaTypes.manifest,
                size=os.stat(sha256_path / manifest_SHA).st_size,
                digest=f"sha256:{manifest_SHA}",
                urls = None,
            )
        ]
    )
    index_json = json.dumps(index.dict(exclude_none=True), indent=4, sort_keys=True)
    with open(dest_dir / "index.json", "w") as f:
        f.write(index_json)

    # Create the OCI-layout file
    oci_layout = create_ocilayout()
    with open(dest_dir / "oci-layout", "w") as f:
        f.write(json.dumps(oci_layout.model_dump(), indent=4, sort_keys=True))

    # Create empty config file with digest as name
    empty_config: dict[str, str] = {}
    empty_digest_split = Values.empty_digest.split(":")
    if len(empty_digest_split) == 2:
        with open(dest_dir / "blobs" / "sha256" / empty_digest_split[1], "w") as f:
            f.write(json.dumps(empty_config))
    else:
        raise ValueError(f"Invalid empty_digest format: {Values.empty_digest}")

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

if __name__ == "__main__":
    main()
