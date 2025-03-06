
import logging
import os
from pathlib import Path
from pprint import pprint
import tarfile
from typing import Dict, List, Sequence
import typing

from olot.oci.oci_config import OCIManifestConfig

from olot.oci.oci_image_index import OCIImageIndex, read_ocilayout_root_index
from olot.oci.oci_image_manifest import OCIImageManifest, ContentDescriptor
from olot.oci.oci_image_layout import verify_ocilayout
from olot.oci.oci_common import MediaTypes

from olot.utils.files import handle_remove, tarball_from_file, targz_from_file
from olot.utils.types import compute_hash_of_str

logger = logging.getLogger(__name__)

def oci_layers_on_top(
        ocilayout: typing.Union[str, os.PathLike],
        model_files: Sequence[os.PathLike],
        modelcard: typing.Union[os.PathLike, None] = None,
        *,
        remove_originals: bool = False):
    """
    Add contents to an oci-layout directory as new blob layers

    Args:
        ocilayout: The oci-layout directory of the base image.
        model_files: PathLike array to be added as new blob layers.
        modelcard: PathLike of the README.md of the ModelCarD, will be added as the last layer with compression and annotations.
        remove: whether to remove the original content files after having added the layers, default: False.
    """
    if not isinstance(ocilayout, Path):
        ocilayout = Path(ocilayout)
    if remove_originals:
        logger.info("Invoked with 'remove' to delete original contents after adding as a blob layer.")

    verify_ocilayout(ocilayout)
    ocilayout_root_index: OCIImageIndex = read_ocilayout_root_index(ocilayout)
    ocilayout_indexes: Dict[str, OCIImageIndex] = crawl_ocilayout_indexes(ocilayout, ocilayout_root_index)
    ocilayout_manifests: Dict[str, OCIImageManifest] = crawl_ocilayout_manifests(ocilayout, ocilayout_indexes, ocilayout_root_index)
    new_layers = {} # layer digest : diff_id

    sha256_path = ocilayout / "blobs" / "sha256"
    for model in model_files:
        model = Path(model)
        new_layer = tarball_from_file(model, sha256_path)
        new_layers[new_layer] = new_layer
        if remove_originals:
            handle_remove(model)
    if modelcard is not None:
        modelcard_layer_diffid = targz_from_file(Path(modelcard), sha256_path)
        new_layers[modelcard_layer_diffid[0]] = modelcard_layer_diffid[1]
        if remove_originals:
            handle_remove(modelcard)

    new_ocilayout_manifests: Dict[str, str] = {}
    for manifest_hash, manifest in ocilayout_manifests.items():
        print(manifest_hash, manifest.mediaType)
        config_sha = manifest.config.digest.removeprefix("sha256:")
        mc = None
        with open(ocilayout / "blobs" / "sha256" / config_sha, "r") as cf:
            mc = OCIManifestConfig.model_validate_json(cf.read())
        for layer, diffid in new_layers.items():
            size = os.stat(ocilayout / "blobs" / "sha256" / layer).st_size
            mt = MediaTypes.layer if layer == diffid else MediaTypes.layer_gzip
            la = None if layer == diffid else {"io.opendatahub.temp.layer.type":"modelcard"}
            cd = ContentDescriptor(
                mediaType=mt,
                digest="sha256:"+layer,
                size=size,
                urls=None,
                data=None,
                artifactType=None,
                annotations=la
            )
            mc.rootfs.diff_ids.append("sha256:"+diffid)
            manifest.layers.append(cd)
        # TODO: add to Manifest.config the history/author of this project.
        mc_json = mc.model_dump_json(exclude_none=True)
        with open(ocilayout / "blobs" / "sha256" / config_sha, "w") as cf:
            cf.write(mc_json)
        mc_json_hash = compute_hash_of_str(mc_json)
        os.rename(ocilayout / "blobs" / "sha256" / config_sha, ocilayout / "blobs" / "sha256" / mc_json_hash)
        print(f"Renamed config from: {config_sha} to {mc_json_hash}")
        config_sha = mc_json_hash
        manifest.config.digest = "sha256:" + config_sha
        manifest.config.size = os.stat(ocilayout / "blobs" / "sha256" / config_sha).st_size
        if manifest.annotations is None:
            manifest.annotations = {}
        manifest.annotations["io.opendatahub.temp.author"] = "olot"
        manifest_json = manifest.model_dump_json(exclude_none=True)
        with open(ocilayout / "blobs" / "sha256" / manifest_hash, "w") as cf:
            cf.write(manifest_json)
        manifest_json_hash = compute_hash_of_str(manifest_json)
        os.rename(ocilayout / "blobs" / "sha256" / manifest_hash, ocilayout / "blobs" / "sha256" / manifest_json_hash)
        print(f"Renamed Manifest from: {manifest_hash} to {manifest_json_hash}")
        new_ocilayout_manifests[manifest_hash] = manifest_json_hash
        manifest_hash = manifest_json_hash
    pprint(new_ocilayout_manifests)
    new_ocilayout_indexes: Dict[str, str] = {}
    for index_hash, index in ocilayout_indexes.items():
        print(index_hash, index.mediaType)
        for m in index.manifests:
            lookup_new_hash = new_ocilayout_manifests[m.digest.removeprefix("sha256:")]
            print(f"old manifest {m.digest} is now at {lookup_new_hash}")
            m.digest = "sha256:" + lookup_new_hash
            m.size = os.stat(ocilayout / "blobs" / "sha256" / lookup_new_hash).st_size
        index_json = index.model_dump_json(exclude_none=True)
        with open(ocilayout / "blobs" / "sha256" / index_hash, "w") as idxf:
            idxf.write(index_json)
        index_json_hash = compute_hash_of_str(index_json)
        os.rename(ocilayout / "blobs" / "sha256" / index_hash, ocilayout / "blobs" / "sha256" / index_json_hash)
        print(f"Renamed Index from: {index_hash} to {index_json_hash}")
        new_ocilayout_indexes[index_hash] = index_json_hash
    pprint(new_ocilayout_indexes)
    for entry in ocilayout_root_index.manifests:
        if entry.mediaType == MediaTypes.index:
            lookup_new_hash = new_ocilayout_indexes[entry.digest.removeprefix("sha256:")]
            print(f"old index {entry.digest} is now at {lookup_new_hash}")
            entry.digest = "sha256:" + lookup_new_hash
            entry.size = os.stat(ocilayout / "blobs" / "sha256" / lookup_new_hash).st_size
        elif entry.mediaType == MediaTypes.manifest:
            lookup_new_hash = new_ocilayout_manifests[entry.digest.removeprefix("sha256:")]
            print(f"old index {entry.digest} is now at {lookup_new_hash}")
            entry.digest = "sha256:" + lookup_new_hash
            entry.size = os.stat(ocilayout / "blobs" / "sha256" / lookup_new_hash).st_size
        else:
            raise ValueError(f"unknown root index mediaType {entry.mediaType}")
    with open(ocilayout / "index.json", "w") as root_idx_f:
        root_idx_f.write(ocilayout_root_index.model_dump_json(exclude_none=True))



def crawl_ocilayout_manifests(ocilayout: Path, ocilayout_indexes: Dict[str, OCIImageIndex], ocilayout_root_index: typing.Union[OCIImageIndex, None] = None) -> Dict[str, OCIImageManifest]:
    """crawl Manifests from referred OCI Index(es) and Manifests in the root index of the oci-layout
    """
    ocilayout_manifests: Dict[str, OCIImageManifest]  = {}
    for _, mi in ocilayout_indexes.items():
        for m in mi.manifests:
            logger.debug("Parsing manifest %s", m)
            if m.mediaType != MediaTypes.manifest:
                raise ValueError("Did not expect something else than Image Manifest in a Index")
            target_hash = m.digest.removeprefix("sha256:")
            logger.debug("target_hash %s", target_hash)
            manifest_path = ocilayout / "blobs" / "sha256" / target_hash
            with open(manifest_path, "r") as ip:
                ocilayout_manifests[target_hash] = OCIImageManifest.model_validate_json(ip.read())
    if ocilayout_root_index is None:
        return ocilayout_manifests # return early
    for m in ocilayout_root_index.manifests:
        if m.mediaType == MediaTypes.manifest:
            target_hash = m.digest.removeprefix("sha256:")
            logger.debug("Lookup remainder manifest from ocilayout_root_index having target_hash %s", target_hash)
            manifest_path = ocilayout / "blobs" / "sha256" / target_hash
            with open(manifest_path, "r") as ip:
                ocilayout_manifests[target_hash] = OCIImageManifest.model_validate_json(ip.read())
    return ocilayout_manifests


def crawl_ocilayout_indexes(ocilayout: Path, ocilayout_root_index: OCIImageIndex) -> Dict[str, OCIImageIndex] :
    ocilayout_indexes: Dict[str, OCIImageIndex] = {}
    for m in ocilayout_root_index.manifests:
        if m.mediaType == MediaTypes.index:
            target_hash = m.digest.removeprefix("sha256:")
            index_path = ocilayout / "blobs" / "sha256" / target_hash
            with open(index_path, "r") as ip:
                ocilayout_indexes[target_hash] = OCIImageIndex.model_validate_json(ip.read())
    return ocilayout_indexes


def crawl_ocilayout_blobs_to_extract(ocilayout: Path, 
                                     output_path: Path,
                                     tar_filter_dir: str = "/models") -> List[str]:
    """
    Extract from OCI Image/ModelCar only the contents from a specific directory.

    Args:
        ocilayout: The directory containing the oci-layout of the OCI Image/ModelCar.
        output_path: The directory where to extract the ML model assets from the ModelCar to.
        tar_filter_dir: The subdirectory in the ModelCar to extract, defaults to `"/models"`.

    Returns:
        The list of extracted ML contents from the OCI Image/ModelCar.
    """
    extracted: List[str] = []
    tar_filter_dir= tar_filter_dir.lstrip("/")
    blobs_path = ocilayout / "blobs" / "sha256"
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    verify_ocilayout(ocilayout)
    ocilayout_root_index = read_ocilayout_root_index(ocilayout)
    if len(ocilayout_root_index.manifests) != 1:
        raise ValueError("TODO the root index has more than one manifest, expected single ModelCar")
    manifest0 = ocilayout_root_index.manifests[0]
    if manifest0.mediaType != MediaTypes.manifest:
        raise ValueError("Can only extract from ModelCar Image manifests")
    target_hash = manifest0.digest.removeprefix("sha256:")
    manifest_path = blobs_path / target_hash
    with open(manifest_path, "r") as ip:
        image_manifest = OCIImageManifest.model_validate_json(ip.read())
    for layer in image_manifest.layers:
        if layer.mediaType == MediaTypes.layer or layer.mediaType == MediaTypes.layer_gzip:
            target_hash = layer.digest.removeprefix("sha256:")
            manifest_path = blobs_path / target_hash
            with tarfile.open(manifest_path, "r:*") as tar:
                for member in tar.getmembers():
                    if member.isfile() and member.name.startswith(tar_filter_dir):
                        tar.extract(member, path=output_path)
                        extracted.append(member.name)
    return extracted


if __name__ == "__main__":
    print("?")
