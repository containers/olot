import hashlib
import logging
import shutil
import tarfile
from pathlib import Path
import gzip
import os

logger = logging.getLogger(__name__)

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

class MIMETypes:
    mlmodel = "application/x-mlmodel"
    octet_stream = "application/octet-stream"

def get_file_hash(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(4096):
            h.update(chunk)
    return h.hexdigest()


def tar_filter_fn(input: tarfile.TarInfo) -> tarfile.TarInfo :
    """
    A filter function for modifying file metadata when adding files to a tar archive.

    See also: https://docs.openshift.com/container-platform/4.17/openshift_images/create-images.html#use-uid_create-images

    Args:
        input (tarfile.TarInfo): The file metadata object representing a file being added to the tar archive.

    Returns:
        tarfile.TarInfo: The modified file metadata with the following changes:
            - `uid` set to 0 (root user).
            - `gid` set to 0 (root group).
            - `mode` set to 0o664 (read/write for root owner and root group, read-only for others).
    """
    input.uid = 0
    input.gid = 0
    input.mode = 0o664
    return input


def tarball_from_file(file_path: Path, dest: Path) -> str:
    """
    Creates a tarball from a specified file, storing it in the destination directory with a name based on its checksum.

    Args:
        file_path (Path): The path of the file or directory to be added to the tar archive.
        dest (Path): The destination directory where the tarball will be saved.

    Returns:
        str: The checksum (SHA-256) of the tarball, which is also used as the filename.

    Raises:
        ValueError: If supplied input file path does not exist.
        OSError: If an error occurs during file operations such as renaming or writing.
        tarfile.TarError: If an error occurs during the tar archive creation process.
    """
    if not file_path.exists():
        raise ValueError(f"Input file '{file_path}' does not exist.")

    os.makedirs(dest, exist_ok=True)
    temp_dest = dest / "temp"

    try:
        with open(temp_dest, "wb") as temp_file:
            writer = HashingWriter(temp_file)
            with tarfile.open(fileobj=writer, mode="w") as tar: # type: ignore[call-overload]
                tar.add(file_path, arcname="/models/"+file_path.name, filter=tar_filter_fn)
        checksum = writer.hash_func.hexdigest()
        os.rename(temp_dest, dest / checksum)
        return checksum
    except tarfile.TarError as e:
        raise tarfile.TarError(f"Error creating tarball: {e}") from e
    except OSError as e:
        raise OSError(f"File operation failed: {e}") from e


def targz_from_file(file_path: Path, dest: Path) -> tuple[str, str]:
    """
    Creates a gzipped tarball from the specified file, storing it in the destination directory.
    The tarball's filename is based on the post-compression checksum.

    Args:
        file_path (Path): The path of the file or directory to be compressed.
        dest (Path): The destination directory where the gzipped tarball will be saved. If the directory
                     does not exist, it will be created.

    Returns:
        tuple[str, str]: A tuple containing:
            - The post-compression checksum (SHA-256 of the gzipped tarball).
            - The pre-compression checksum (SHA-256 of the tar content).

    Raises:
        ValueError: If the input file or directory does not exist.
        OSError: If a file operation (e.g., writing, renaming) fails.
        tarfile.TarError: If an error occurs during tarball creation.
    """
    if not file_path.exists():
        raise ValueError(f"Input file '{file_path}' does not exist.")

    os.makedirs(dest, exist_ok=True)
    temp_dest = dest / "temp"

    try:
        with open(temp_dest, "wb") as temp_file:
            writer = HashingWriter(temp_file)
            with gzip.GzipFile(fileobj=writer, mode="wb", mtime=0, compresslevel=6) as gz: # type: ignore[call-overload]
                inner_writer = HashingWriter(gz)
                with tarfile.open(fileobj=inner_writer, mode="w") as tar: # type: ignore[call-overload]
                    tar.add(file_path, arcname="/models/"+file_path.name, filter=tar_filter_fn)
        precompress_checksum = inner_writer.hash_func.hexdigest()
        postcompress_checksum = writer.hash_func.hexdigest()
        os.rename(temp_dest, dest / postcompress_checksum)
        return (postcompress_checksum, precompress_checksum)
    except tarfile.TarError as e:
        raise tarfile.TarError(f"Error creating tarball: {e}") from e
    except OSError as e:
        raise OSError(f"File operation failed: {e}") from e


def handle_remove(path: os.PathLike):
    if not isinstance(path, Path):
        path = Path(path)
    if path.is_symlink():
        logger.warning("removing %s which is a symlink", path)
    if path.is_dir():
        shutil.rmtree(path)
    else:
        os.remove(path)
