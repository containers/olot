
import hashlib
import os
from pathlib import Path
from pprint import pprint
import tarfile
from typing import Dict
import click
import gzip

from .oci.oci_config import OCIManifestConfig

from .oci.oci_image_index import OCIImageIndex
from .oci.oci_image_manifest import OCIImageManifest, ContentDescriptor

from .oci.oci_image_layout import ImageLayoutVersion, OCIImageLayout

class HashingWriter:
    def __init__(self, base_writer, hash_func=None):
        self.base_writer = base_writer
        self.hash_func = hash_func or hashlib.sha256()

    def write(self, data: bytes):
        self.hash_func.update(data)
        return self.base_writer.write(data)
    
    def tell(self):
        return self.base_writer.tell()

    def close(self):
        self.base_writer.close()


def get_file_hash(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()


def oci_layers_on_top(ocilayout: Path, model_files):
    check_ocilayout(ocilayout)
    ocilayout_root_index = read_ocilayout_root_index(ocilayout)
    ocilayout_indexes: Dict[str, OCIImageIndex] = crawl_ocilayout_indexes(ocilayout, ocilayout_root_index)
    ocilayout_manifests: Dict[str, OCIImageManifest] = crawl_ocilayout_manifests(ocilayout, ocilayout_indexes)
    new_layers = []
    for model in model_files:
        model = Path(model)
        new_layer = tar_into_ocilayout(ocilayout, model)
        new_layers.append(new_layer)
    new_ocilayout_manifests: Dict[str, str] = {}
    for manifest_hash, manifest in ocilayout_manifests.items():
        print(manifest_hash, manifest.mediaType)
        config_sha = manifest.config.digest.removeprefix("sha256:")
        mc = None
        with open(ocilayout / "blobs" / "sha256" / config_sha, "r") as cf:
            mc = OCIManifestConfig.model_validate_json(cf.read())
        for layer in new_layers:
            size = os.stat(ocilayout / "blobs" / "sha256" / layer).st_size
            cd = ContentDescriptor(
                mediaType="application/vnd.oci.image.layer.v1.tar",
                digest="sha256:"+layer,
                size=size,
                urls=None,
                data=None,
                artifactType=None           
            )
            mc.rootfs.diff_ids.append("sha256:"+layer)
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
        manifest.annotations["io.opendatahub.temp.author"] = "olot" # type:ignore
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
        if entry.mediaType == "application/vnd.oci.image.index.v1+json":
            lookup_new_hash = new_ocilayout_indexes[entry.digest.removeprefix("sha256:")]
            print(f"old index {entry.digest} is now at {lookup_new_hash}")
            entry.digest = "sha256:" + lookup_new_hash
            entry.size = os.stat(ocilayout / "blobs" / "sha256" / lookup_new_hash).st_size
        elif entry.mediaType == "application/vnd.oci.image.manifest.v1+json":
            lookup_new_hash = new_ocilayout_manifests[entry.digest.removeprefix("sha256:")]
            print(f"old index {entry.digest} is now at {lookup_new_hash}")
            entry.digest = "sha256:" + lookup_new_hash
            entry.size = os.stat(ocilayout / "blobs" / "sha256" / lookup_new_hash).st_size
        else:
            raise ValueError(f"unknown root index mediaType {entry.mediaType}")
    with open(ocilayout / "index.json", "w") as root_idx_f:
        root_idx_f.write(ocilayout_root_index.model_dump_json(exclude_none=True))


def compute_hash_of_str(content: str) -> str:
    h = hashlib.sha256()
    h.update(content.encode())
    return h.hexdigest()


def crawl_ocilayout_manifests(ocilayout: Path, ocilayout_indexes: Dict[str, OCIImageIndex]) -> Dict[str, OCIImageManifest]:
    ocilayout_manifests: Dict[str, OCIImageManifest]  = {}
    for _, mi in ocilayout_indexes.items():
        for m in mi.manifests:
            print(m)
            if m.mediaType != "application/vnd.oci.image.manifest.v1+json":
                raise ValueError("Did not expect something else than Image Manifest in a Index")
            target_hash = m.digest.removeprefix("sha256:")
            print(target_hash)
            manifest_path = ocilayout / "blobs" / "sha256" / target_hash
            with open(manifest_path, "r") as ip:
                ocilayout_manifests[target_hash] = OCIImageManifest.model_validate_json(ip.read())
    return ocilayout_manifests


def crawl_ocilayout_indexes(ocilayout: Path, ocilayout_root_index: OCIImageIndex) -> Dict[str, OCIImageIndex] :
    ocilayout_indexes: Dict[str, OCIImageIndex] = {}
    for m in ocilayout_root_index.manifests:
        if m.mediaType == "application/vnd.oci.image.index.v1+json":
            target_hash = m.digest.removeprefix("sha256:")
            index_path = ocilayout / "blobs" / "sha256" / target_hash
            with open(index_path, "r") as ip:
                ocilayout_indexes[target_hash] = OCIImageIndex.model_validate_json(ip.read())
        else:
            if len(ocilayout_indexes) == 0:
                raise ValueError("TODO the root index has Image manifest")
            else:
                click.echo(f"Found Image Manifest {m.digest} in root index, TODO assuming these are referred through the other indexes")
    return ocilayout_indexes
        

def check_ocilayout(ocilayout: Path):
    with open(ocilayout / "oci-layout", "r") as f:
        m = OCIImageLayout.model_validate_json(f.read())
        if not m.imageLayoutVersion == ImageLayoutVersion.field_1_0_0:
            raise ValueError(f"Unexpected ocilayout in {ocilayout}")


def tar_into_ocilayout(ocilayout: Path, model: Path):
    sha256_path = ocilayout / "blobs" / "sha256"
    temp_tar_filename = sha256_path / "temp_layer"
    with open(temp_tar_filename, "wb") as temp_file:
        writer = HashingWriter(temp_file)
        with tarfile.open(fileobj=writer, mode="w") as tar: # type:ignore
            tar.add(model, arcname="/models/"+model.name, filter=tar_filter_fn)
    checksum = writer.hash_func.hexdigest()
    click.echo(f"digest of the tar file: {checksum}")
    final_tar_filename = checksum
    os.rename(temp_tar_filename, sha256_path / final_tar_filename)
    click.echo(f"tar file renamed to: {final_tar_filename}")
    return checksum


def targz_into_ocilayout(ocilayout: Path, model: Path):
    sha256_path = ocilayout / "blobs" / "sha256"
    temp_tar_filename = sha256_path / "temp_layer"
    with open(temp_tar_filename, "wb") as temp_file:
        writer = HashingWriter(temp_file)
        with gzip.GzipFile(fileobj=writer, mode="wb", mtime=0, compresslevel=6) as gz:
            inner_writer = HashingWriter(gz)
            with tarfile.open(fileobj=inner_writer, mode="w") as tar:
                tar.add(model, arcname="/models/"+model.name, filter=tar_filter_fn)
    checksum = writer.hash_func.hexdigest()
    tar_checksum = inner_writer.hash_func.hexdigest()
    final_tar_filename = checksum
    os.rename(temp_tar_filename, sha256_path / final_tar_filename)
    return (checksum, tar_checksum)


def tar_filter_fn(input: tarfile.TarInfo) -> tarfile.TarInfo :
    input.uid = 0
    input.gid = 0
    input.mode = 0o664
    return input


def read_ocilayout_root_index(ocilayout: Path) -> OCIImageIndex:
    ocilayout_root_index = None
    with open(ocilayout / "index.json", "r") as f:
        ocilayout_root_index = OCIImageIndex.model_validate_json(f.read())
    return ocilayout_root_index


if __name__ == "__main__":
    print("?")
