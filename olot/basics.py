import datetime
from enum import Enum
import logging
import os
from pathlib import Path
from pprint import pprint
import tarfile
from typing import Dict, List, Sequence
import typing

from olot.modelpack.model_config import Model, ModelConfig, ModelDescriptor, ModelFS, Type
from olot.oci.oci_config import HistoryItem, OCIManifestConfig

from olot.oci.oci_image_index import Manifest, OCIImageIndex, Platform, read_ocilayout_root_index
from olot.oci.oci_image_manifest import OCIImageManifest, ContentDescriptor, create_oci_image_manifest
from olot.oci.oci_image_layout import verify_ocilayout
from olot.oci.oci_common import MediaTypes

from olot.utils.files import LayerStats, handle_remove, tarball_from_file, targz_from_file
from olot.utils.types import compute_hash_of_str

from olot.modelpack import const as modelpack_consts

logger = logging.getLogger(__name__)

class CustomStrEnum(str, Enum):
    """To polyfill back to 3.9"""
    @classmethod
    def values(cls) -> Sequence[str]:
        return [e.value for e in cls]
    

class RemoveOriginals(CustomStrEnum):
    """Strategy to be applied when removing original files
    
    default: remove only model weights, configuration, etc.
    all: like default, but also remove the Model CarD"""
    DEFAULT = "default"
    ALL = "all"


def oci_layers_on_top(
        ocilayout: typing.Union[str, os.PathLike],
        model_files: Sequence[os.PathLike],
        modelcard: typing.Union[os.PathLike, None] = None,
        *,
        remove_originals: typing.Union[RemoveOriginals, None] = None,
        add_modelpack: typing.Union[bool, None] = None):
    """
    Add contents to an oci-layout directory as new blob layers

    Args:
        ocilayout: The oci-layout directory of the base image.
        model_files: PathLike array to be added as new blob layers.
        modelcard: PathLike of the README.md of the ModelCarD, will be added as the last layer with compression and annotations.
        remove_originals: whether to remove the original content files after having added the layers, default: None.
        add_modelpack: whether to add a ModelPack manifest to the multi-arch oci-layout only if not already present, default: None.
    """
    if not isinstance(ocilayout, Path):
        ocilayout = Path(ocilayout)
    if remove_originals:
        logger.info("Invoked with remove_originals=%s to delete original contents after adding as a blob layer.", remove_originals.value)

    # Normalize each path in model_files and modelcard to ensure consistency
    model_files = [Path(mf).resolve() for mf in model_files]
    if modelcard is not None:
        modelcard = Path(modelcard).resolve()

    verify_ocilayout(ocilayout)
    ocilayout_root_index: OCIImageIndex = read_ocilayout_root_index(ocilayout)
    ocilayout_indexes: Dict[str, OCIImageIndex] = crawl_ocilayout_indexes(ocilayout, ocilayout_root_index)
    ocilayout_manifests: Dict[str, OCIImageManifest] = crawl_ocilayout_manifests(ocilayout, ocilayout_indexes, ocilayout_root_index)
    new_layers: Dict[str, LayerStats] = {} # layer digest : diff_id

    # check configuration is consistent
    add_modelpack = check_and_sanitize_flag_add_modelpack(add_modelpack, ocilayout_indexes, ocilayout_manifests)
    if modelcard in model_files:
        if remove_originals:
            raise ValueError("ModelCard detected, while remove_originals flag is set; this is not allowed as it would remove the original ModelCard before having a chance of adding it as its proper layer.")
        else:
            logger.warning("ModelCard detected in model_files, this will result in duplicated layers for the ModelCard (negligible, but not optimal).")

    sha256_path = ocilayout / "blobs" / "sha256"
    for model in model_files:
        model = Path(model)
        new_layer = tarball_from_file(model, sha256_path)
        new_layers[new_layer.layer_digest] = new_layer
        if remove_originals:
            handle_remove(model)
    if modelcard is not None:
        new_layer = targz_from_file(Path(modelcard), sha256_path)
        new_layers[new_layer.layer_digest] = new_layer
        if remove_originals == RemoveOriginals.ALL:
            handle_remove(modelcard)

    new_ocilayout_manifests: Dict[str, str] = {}
    for manifest_hash, manifest in ocilayout_manifests.items():
        print(manifest_hash, manifest.mediaType)
        config_sha = manifest.config.digest.removeprefix("sha256:")
        mc = None
        with open(ocilayout / "blobs" / "sha256" / config_sha, "r") as cf:
            mc = OCIManifestConfig.model_validate_json(cf.read())
            if mc.history is None:
                mc.history = []
        for new_layer in new_layers.values():
            layer_digest = new_layer.layer_digest
            layer_stat = os.stat(ocilayout / "blobs" / "sha256" / layer_digest)
            size = layer_stat.st_size
            ctime = layer_stat.st_ctime
            mt = MediaTypes.layer if layer_digest == new_layer.diff_id else MediaTypes.layer_gzip
            la = {"org.opencontainers.image.title": new_layer.title} # if ever used for OCI artifact, add `unpack` annotations 
            is_modelcard = layer_digest != new_layer.diff_id
            if is_modelcard:
                la["io.opendatahub.modelcar.layer.type"] = "modelcard"
            cd = ContentDescriptor(
                mediaType=mt,
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
                created_by="olot oci_layers_on_top "+new_layer.title+(" (modelcard)" if is_modelcard else "")
            )
            mc.history.append(hi)
            manifest.layers.append(cd)
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
        manifest.annotations["io.opendatahub.author"] = "olot"
        if modelcard is not None:
            manifest.annotations["io.opendatahub.layers.modelcard"] = "sha256:"+next(reversed(new_layers.keys())) # identify ModelCarD layer from Image Manifest
        check_manifest(manifest, mc)
        manifest_json = manifest.model_dump_json(exclude_none=True)
        with open(ocilayout / "blobs" / "sha256" / manifest_hash, "w") as cf:
            cf.write(manifest_json)
        manifest_json_hash = compute_hash_of_str(manifest_json)
        os.rename(ocilayout / "blobs" / "sha256" / manifest_hash, ocilayout / "blobs" / "sha256" / manifest_json_hash)
        print(f"Renamed Manifest from: {manifest_hash} to {manifest_json_hash}")
        new_ocilayout_manifests[manifest_hash] = manifest_json_hash
        manifest_hash = manifest_json_hash
    pprint(new_ocilayout_manifests)
    if add_modelpack:
        modelpack_manifest_hash = add_modelpack_manifest(ocilayout, new_layers)
    
    new_ocilayout_indexes: Dict[str, str] = {}
    for index_hash, index in ocilayout_indexes.items():
        print(index_hash, index.mediaType)
        for m in index.manifests:
            digest = m.digest.removeprefix("sha256:")
            if digest in new_ocilayout_manifests.keys():
                lookup_new_hash = new_ocilayout_manifests[m.digest.removeprefix("sha256:")]
                logger.info("old manifest %s is now at %s", m.digest, lookup_new_hash)
                m.digest = "sha256:" + lookup_new_hash
                m.size = os.stat(ocilayout / "blobs" / "sha256" / lookup_new_hash).st_size
            else:
                logger.info("manifest %s was unchanged", digest)
        if add_modelpack:
            if modelpack_manifest_hash in [m.digest.removeprefix("sha256:") for m in index.manifests]:
                raise ValueError(f"ModelPack manifest already present in Index {index_hash} while add_modelpack=True")
            else:
                logger.debug("adding ModelPack manifest to the index %s", index_hash)
                index.manifests.append(Manifest(
                    mediaType=MediaTypes.manifest,
                    digest="sha256:"+modelpack_manifest_hash,
                    size=os.stat(ocilayout / "blobs" / "sha256" / modelpack_manifest_hash).st_size,
                    urls=None,
                    platform=Platform( # type: ignore[call-arg]
                        architecture="unknown",
                        os="unknown",
                    ),
                    annotations={"io.opendatahub.author": "olot", "io.opendatahub.modelcar.manifest.type":"modelpack"},
                ))
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
            digest = entry.digest.removeprefix("sha256:")
            if digest in new_ocilayout_manifests.keys():
                lookup_new_hash = new_ocilayout_manifests[entry.digest.removeprefix("sha256:")]
                logger.info("old manifest %s is now at %s", entry.digest, lookup_new_hash)
                entry.digest = "sha256:" + lookup_new_hash
                entry.size = os.stat(ocilayout / "blobs" / "sha256" / lookup_new_hash).st_size
            else:
                logger.info("manifest %s was unchanged", digest)
        else:
            raise ValueError(f"unknown root index mediaType {entry.mediaType}")
    if add_modelpack:
        if modelpack_manifest_hash in [m.digest.removeprefix("sha256:") for m in ocilayout_root_index.manifests]:
            raise ValueError("ModelPack manifest already present in Root index in oci-layout, while add_modelpack=True")
        else:
            logger.debug("adding ModelPack manifest to the root index")
            ocilayout_root_index.manifests.append(Manifest(
                mediaType=MediaTypes.manifest,
                digest="sha256:"+modelpack_manifest_hash,
                size=os.stat(ocilayout / "blobs" / "sha256" / modelpack_manifest_hash).st_size,
                urls=None,
                platform=Platform( # type: ignore[call-arg]
                    architecture="unknown",
                    os="unknown",
                ),
                annotations={"io.opendatahub.author": "olot", "io.opendatahub.modelcar.manifest.type":"modelpack"},
            ))
    with open(ocilayout / "index.json", "w") as root_idx_f:
        root_idx_f.write(ocilayout_root_index.model_dump_json(exclude_none=True))


def add_modelpack_manifest(ocilayout: Path, new_layers: Dict[str, LayerStats]) -> str:
    """add a ModelPack manifest to the oci-layout
    """
    model_config = Model(
        descriptor=ModelDescriptor(name=None), # eventually config and metadata will be provided programmatically
        modelfs=ModelFS(type=Type.layers, diffIds=list(b.diff_id for b in new_layers.values())),
        config=ModelConfig(),
    )
    model_config_json = model_config.model_dump_json(exclude_none=True)
    model_config_hash = compute_hash_of_str(model_config_json)
    with open(ocilayout / "blobs" / "sha256" / model_config_hash, "w") as mpcf:
        mpcf.write(model_config_json)
    cds = []
    for layer in new_layers.values():
        layer_digest = layer.layer_digest
        layer_stat = os.stat(ocilayout / "blobs" / "sha256" / layer_digest)
        size = layer_stat.st_size
        la = {"org.opencontainers.image.title": layer.title}
        is_modelcard = layer_digest != layer.diff_id
        mt = modelpack_consts.MEDIATYPEMODELDOCGZIP if is_modelcard else modelpack_consts.MEDIATYPEMODELWEIGHT
        cd = ContentDescriptor(
            mediaType=mt,
            digest="sha256:"+layer_digest,
            size=size,
            urls=None,
            data=None,
            artifactType=None,
            annotations=la
        )
        cds.append(cd)
    manifest = create_oci_image_manifest(
        mediaType=MediaTypes.manifest, # default already, but for expliciting here Modelpack spec adherence
        artifactType=modelpack_consts.ARTIFACTTYPEMODELMANIFEST,
        config=ContentDescriptor(
            mediaType=modelpack_consts.MEDIATYPEMODELCONFIG,
            artifactType=None,
            digest="sha256:"+model_config_hash,
            size=os.stat(ocilayout / "blobs" / "sha256" / model_config_hash).st_size,
            urls=None,
            data=None,
        ),
        layers=cds
    )
    manifest_json = manifest.model_dump_json(exclude_none=True)
    manifest_hash = compute_hash_of_str(manifest_json)
    with open(ocilayout / "blobs" / "sha256" / manifest_hash, "w") as mf:
        mf.write(manifest_json)
    return manifest_hash


def check_and_sanitize_flag_add_modelpack(add_modelpack: typing.Union[bool, None], ocilayout_indexes: Dict[str, OCIImageIndex], ocilayout_manifests: Dict[str, OCIImageManifest]) -> bool:
    """Check and sanitize the add_modelpack flag
    - check if the oci-layout contains an Index manifest for multi-arch, othewise fail: can't add a ModelPack manifest to a single-arch oci-layout
      this is because a single-arch is a single OCI Image Manifest and not introducing an Index; hence, can't add a ModelPack manifest to the non-existing Index which is tagged (`:latest`) by the oci-layout root index
    - sanitize the add_modelpack flag to avoid adding a ModelPack manifest if it's already present in the oci-layout
    """
    if add_modelpack:
        if len(ocilayout_indexes) == 0:
            raise ValueError("Can't add a ModelPack manifest to a single-arch oci-layout")
        logger.debug("checking if ModelPack manifest is alreadypresent in the oci-layout")
        for manifest_hash, manifest in ocilayout_manifests.items():
            if manifest.artifactType == modelpack_consts.ARTIFACTTYPEMODELMANIFEST:
                logger.warning("ModelPack manifest already present in the oci-layout as %s; will IGNORE add_modelpack=True", manifest_hash)
                return False
    return add_modelpack or False # leave unchanged unless of sanitization requirements above, if None just return False


def check_manifest(manifest: OCIImageManifest, config: OCIManifestConfig):
    """perform some sanity check on the manifests required for additional scenarios of usage
    """
    ch_count = len(list(x for x in config.history if not x.empty_layer)) if config.history else 0
    layers_count = len(manifest.layers)
    if layers_count != ch_count:
        raise ValueError(f"history lists {ch_count} non-empty layers, but there are {layers_count} layers in the image manifest")


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
    for m in ocilayout_root_index.manifests if ocilayout_root_index is not None else []:
        if m.mediaType == MediaTypes.manifest:
            target_hash = m.digest.removeprefix("sha256:")
            logger.debug("Lookup remainder manifest from ocilayout_root_index having target_hash %s", target_hash)
            manifest_path = ocilayout / "blobs" / "sha256" / target_hash
            with open(manifest_path, "r") as ip:
                ocilayout_manifests[target_hash] = OCIImageManifest.model_validate_json(ip.read())

    # filter out non-runnable OCI Images, like Vendor'd Attestations format, and log it out
    filtered: Dict[str, OCIImageManifest]  = {}
    for k, v in ocilayout_manifests.items():
        if v.layers[0].mediaType == "application/vnd.in-toto+json" or v.artifactType == "application/vnd.docker.attestation.manifest.v1+json":
            logger.info("skipping %s as it's an Attestation manifest", k) # not adding this to filtered list of manifests.
        else:
            filtered[k] = v

    return filtered


def write_empty_config_in_ocilayoyt(ocilayout: Path):
    """small utility to avoid limitation of skopeo that can't read inline empty config
    """
    blobs_path = ocilayout / "blobs" / "sha256"
    blobs_path.mkdir(parents=True, exist_ok=True)
    with open(blobs_path / "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a", 'w') as f:
        f.write("{}")


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
