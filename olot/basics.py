
from dataclasses import dataclass
import hashlib
import json
from typing import List

from pydantic import TypeAdapter
from .oci.oci_image_layout import OCIImageLayout
from .oci.oci_image_index import Manifest, OCIImageIndex
from .oci.oci_common import MediaType
from .oci.oci_image_manifest import OCIImageManifest
from .oci.oci_config import OCIManifestConfig

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
    print("?")
