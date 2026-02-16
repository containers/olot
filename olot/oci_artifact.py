import datetime
from pathlib import Path
import os
import json
from typing import List, Union

from olot.constants import ANNOTATION_LAYER_CONTENT_NAME
from olot.oci.oci_config import HistoryItem, OCIManifestConfig, Rootfs, Type
from olot.oci.oci_image_manifest import ContentDescriptor, create_oci_image_manifest, create_manifest_layers
from olot.oci.oci_image_layout import ImageLayoutVersion, OCIImageLayout, create_ocilayout
from olot.oci.oci_common import MediaTypes, Values
from olot.oci.oci_image_index import Manifest, OCIImageIndex, create_oci_image_index
from olot.utils.files import MIMETypes, tarball_from_file, targz_from_file, walk_files
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
            new_layer = targz_from_file(model_file, sha256_path)
            postcomp_chksum = new_layer.layer_digest
            precomp_chksum = new_layer.diff_id     
            layers[file_name] = (precomp_chksum, postcomp_chksum)
        else:
            new_layer = tarball_from_file(model_file, sha256_path)
            checksum = new_layer.layer_digest
            layers[file_name] = (checksum, "")
    return layers


def create_simple_oci_artifact(source_path: Path,
                               oci_layout_path: Path,
                               artifact_type: Union[str, None] = None,
                               subject: Union[ContentDescriptor, None] = None,
                               annotations: Union[dict[str, str], None] = None):
    """
    Create a simple OCI artifact from a source directory.
    """
    if not source_path.is_dir():
        raise NotADirectoryError(f"Input directory {str(source_path)!r} does not exist.")
    if not oci_layout_path.is_dir():
        raise NotADirectoryError(f"Output directory '{str(oci_layout_path)!r}' does not exist.")
    
    walked_files = walk_files(source_path)

    blobs_path = oci_layout_path / "blobs" / "sha256"
    blobs_path.mkdir(parents=True, exist_ok=True)

    mc = OCIManifestConfig(os="unknown",
                           architecture="unknown",
                           **{"os.version": None, "os.features": None},
                           rootfs=Rootfs(type=Type.layers, diff_ids=[]),
                           history=[],
                           )
    cds = []
    for e in walked_files:
        prefix = str(e.parent) + "/" if e.parent != Path(".") else "/"
        new_layer = targz_from_file(source_path / e, blobs_path, prefix=prefix)
        layer_digest = new_layer.layer_digest
        layer_stat = os.stat(blobs_path / layer_digest)
        size = layer_stat.st_size
        ctime = layer_stat.st_ctime
        title = prefix + e.name if prefix != "/" else e.name
        la = {ANNOTATION_LAYER_CONTENT_NAME: title}  # cannot use org.opencontainers.image.title to avoid oras not untarring the blob :(
        cd = ContentDescriptor(
            mediaType=MediaTypes.layer_gzip,
            digest="sha256:"+layer_digest,
            size=size,
            urls=None,
            data=None,
            artifactType=None,
            annotations=la
        )
        mc.rootfs.diff_ids.append("sha256:"+new_layer.diff_id)
        hi = HistoryItem(
            created=datetime.datetime.fromtimestamp(ctime, tz=datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
            created_by="olot create_simple_oci_artifact "+title,
        )
        if mc.history is not None:
            mc.history.append(hi)
        cds.append(cd)
    mc_json = mc.model_dump_json(exclude_none=True)
    mc_json_hash = compute_hash_of_str(mc_json)
    (blobs_path / mc_json_hash).write_text(mc_json)
    manifest = create_oci_image_manifest(
        config=ContentDescriptor(
                mediaType=MediaTypes.config,
                digest="sha256:" + mc_json_hash,
                size=os.stat(blobs_path / mc_json_hash).st_size,
                urls=None,
                data=None,
                artifactType=None,
            ),
        artifactType=artifact_type,
        layers=cds,
        subject=subject,
        annotations=annotations
        )
    manifest_json = manifest.model_dump_json(indent=2, exclude_none=True)
    manifest_SHA = compute_hash_of_str(manifest_json)
    manifest_blob_path = blobs_path / manifest_SHA
    manifest_blob_path.write_text(manifest.model_dump_json(indent=2, exclude_none=True))
    
    layout = OCIImageLayout(imageLayoutVersion=ImageLayoutVersion.field_1_0_0)
    (oci_layout_path / "oci-layout").write_text(layout.model_dump_json(indent=2, exclude_none=True))

    index = OCIImageIndex(schemaVersion=2,
                          mediaType=MediaTypes.index,
                          manifests=[
                              Manifest(mediaType=MediaTypes.manifest,
                                       size=os.stat(manifest_blob_path).st_size,
                                       digest="sha256:"+manifest_SHA,
                                       annotations={"org.opencontainers.image.ref.name": "latest"},
                                       urls=None,
                                       )
                          ],
                          artifactType=None,
                          )
    (oci_layout_path / "index.json").write_text(index.model_dump_json(indent=2, exclude_none=True))
