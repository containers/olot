import os
import shutil
import subprocess
import typing

def is_oras() -> bool :
    return shutil.which("oras") is not None


def oras_pull(base_image: str, dest: typing.Union[str, os.PathLike]):
    if isinstance(dest, os.PathLike):
        dest = str(dest)
    subprocess.run(["oras", "copy", "--to-oci-layout", base_image, dest+":latest"], check=True)
    blobs_dir = os.path.join(dest, "blobs", "sha256")
    for _, _, files in os.walk(blobs_dir):
        for file in files:
            os.chmod(os.path.join(blobs_dir, file), 0o664) # TODO eventually avoid this by refactor manifest change logic



def oras_push(src: typing.Union[str, os.PathLike], oci_ref: str):
    if isinstance(src, os.PathLike):
        src = str(src)
    return subprocess.run(["oras", "copy", "--from-oci-layout", "--to-plain-http", src+":latest", oci_ref], check=True)
