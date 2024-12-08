
from dataclasses import dataclass
import hashlib
import json
from oci.oci_image_layout import OCIImageLayout
from oci.oci_image_index import MediaType, OCIImageIndex

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

    MediaType.model_validate_json("\"asd/asd\"")