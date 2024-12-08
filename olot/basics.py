
from dataclasses import dataclass
import hashlib
import json
from typing import List

from pydantic import TypeAdapter
from oci.oci_image_layout import OCIImageLayout
from oci.oci_image_index import Manifest, OCIImageIndex
from oci.oci_common import MediaType
from olot.oci.oci_image_manifest import OCIImageManifest
from olot.oci.oci_config import OCIManifestConfig

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

if __name__ == "__main__":
    with open("download/oci-layout", "r") as f:
        m = OCIImageLayout.model_validate_json(f.read())
        print(m)
    with open("download/index.json", "r") as f:
        m = OCIImageIndex.model_validate_json(f.read())
        print(m)
        print(m.manifests[0].size)
        print(m.model_dump_json(exclude_none=True))

    ta = TypeAdapter(MediaType)
    ta.validate_python("asd/asd")

    with open("download/blobs/sha256/db142d433cdde11f10ae479dbf92f3b13d693fd1c91053da9979728cceb1dc68", "r") as f:
        m = OCIImageIndex.model_validate_json(f.read())
        print(m)
        for manifest in m.manifests:
            print(manifest.platform)
            print(manifest.digest)

    with open("download/blobs/sha256/a3e1b257b47c09c9997212e53a0b570c1666501ad26e5bf33461304babab47c7", "r") as f:
        m = OCIImageManifest.model_validate_json(f.read())
        print(m)
        print(m.config.digest)

    with open("download/blobs/sha256/517b897a6a8312ce202a85c8a517d820b0fc5b6f5d14ec2a3267906f75680403", "r") as f:
        m = OCIManifestConfig.model_validate_json(f.read())
        print(m)
        print(m.rootfs)
        print(m.history)
