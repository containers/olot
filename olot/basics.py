
from dataclasses import dataclass
import hashlib


@dataclass
class HashingWriter:
    base_writer: any
    hash_func: any = hashlib.sha256()

    def write(self, data: bytes):
        self.base_writer.write(data)
        self.hash_func.update(data)
    
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
