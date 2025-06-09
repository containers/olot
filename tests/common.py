from pathlib import Path
import tarfile
import gzip
import shutil
from olot.utils.files import HashingWriter, get_file_hash, tar_filter_fn

def get_test_data_path() -> Path:
    """prefixed with get_ to avoid strict enforcement/getting picked up by pytest
    """
    return Path(__file__).parent / "data"

def sample_model_path() -> Path:
    return get_test_data_path() / "sample-model"

def sha256_path(base_path: Path) -> Path:
    return base_path / "blobs" / "sha256"

def file_checksums_without_compression(source_file: Path, tmp_dest: Path) -> str:

    tmp_dest.mkdir(parents=True, exist_ok=True)
    temp_tar_filename = tmp_dest / "temp_layer"

    with open(temp_tar_filename, "wb") as temp_file:
        writer = HashingWriter(temp_file)
        with tarfile.open(fileobj=writer, mode="w") as tar: # type: ignore[call-overload]
            tar.add(source_file, arcname="/models/"+source_file.name, filter=tar_filter_fn)
    sha = get_file_hash(temp_tar_filename)
    shutil.rmtree(tmp_dest)
    return sha


def file_checksums_with_compression(source_file: Path, tmp_dest: Path) -> tuple[str, str]:
    temp_tar_filename = tmp_dest / "temp_layer.tar.gz"

    with open(temp_tar_filename, "wb") as temp_file:
        writer = HashingWriter(temp_file)
        with gzip.GzipFile(fileobj=writer, mode="wb", mtime=0, compresslevel=6) as gz: # type: ignore[call-overload]
            inner_writer = HashingWriter(gz)
            with tarfile.open(fileobj=inner_writer, mode="w") as tar: # type: ignore[call-overload]
                tar.add(source_file, arcname="/models/"+source_file.name, filter=tar_filter_fn)

    postcompress_chksum_from_disk = get_file_hash(temp_tar_filename)

    uncompressed_tar = tmp_dest / "uncompressed.tar"
    with tarfile.open(uncompressed_tar, mode="w") as tar: # type: ignore[call-overload]
        tar.add(source_file, arcname=source_file.name)
    uncompressed_checksum_from_disk = get_file_hash(uncompressed_tar)

    shutil.rmtree(tmp_dest)

    return postcompress_chksum_from_disk, uncompressed_checksum_from_disk