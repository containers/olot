
from typing import Annotated, List
from pydantic import AnyUrl, Field
from pathlib import Path
import os

from olot.utils.files import tarball_from_file, targz_from_file

MediaType = Annotated[str, Field(
        ...,
        pattern=r'^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$'
    )]

class MediaTypes:
    """Constant values from OCI Image Manifest spec

    See also: https://github.com/opencontainers/image-spec/blob/main/media-types.md
    """
    manifest: MediaType = "application/vnd.oci.image.manifest.v1+json"
    index: MediaType = "application/vnd.oci.image.index.v1+json"
    layer: MediaType = "application/vnd.oci.image.layer.v1.tar"
    layer_gzip: MediaType = "application/vnd.oci.image.layer.v1.tar+gzip"


Digest = Annotated[str, Field(
        ...,
        pattern=r'^[a-z0-9]+(?:[+._-][a-z0-9]+)*:[a-zA-Z0-9=_-]+$',
        description="the cryptographic checksum digest of the object, in the pattern '<algorithm>:<encoded>'",
    )]


Urls = Annotated[List[AnyUrl],Field(
        ..., description='a list of urls from which this object may be downloaded'
    )]


def create_blobs(source_dir: Path, oci_dir: Path):
    if not source_dir.exists():
        raise ValueError(f"Input directory '{source_dir}' does not exist.")

    sha256_path = oci_dir / "blobs" / "sha256"
    os.makedirs(sha256_path, exist_ok=True)

    layers = {} # layer digest : diff_id

    # assume flat structure for source_dir for now
    # TODO: handle subdirectories appropriately
    model_files = [source_dir / Path(f) for f in os.listdir(source_dir) if os.path.isfile(os.path.join(source_dir, f))]

    for model_file in model_files:

        # handle model card file if encountered - assume README.md is the modelcard
        if os.path.basename(os.path.normpath(model_file)).endswith("README.md"):
            postcomp_chksum, precomp_chksum = targz_from_file(model_file, sha256_path)
            layers[postcomp_chksum] = precomp_chksum
        else:
            checksum = tarball_from_file(model_file, sha256_path)
            layers[checksum] = checksum
    return layers