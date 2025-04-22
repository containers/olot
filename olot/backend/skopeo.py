import os
import shutil
import subprocess
import typing

def is_skopeo() -> bool :
    return shutil.which("skopeo") is not None


def skopeo_pull(base_image: str, dest: typing.Union[str, os.PathLike], params: typing.Sequence[str]=[]):
    if isinstance(dest, os.PathLike):
        dest = str(dest)
    return subprocess.run(["skopeo", "copy", "--multi-arch", "all", *params, "--remove-signatures", "docker://"+base_image, "oci:"+dest+":latest"], check=True)


def skopeo_push(src: typing.Union[str, os.PathLike], oci_ref: str, params: typing.Sequence[str]=[]):
    if isinstance(src, os.PathLike):
        src = str(src)
    return subprocess.run(["skopeo", "copy", "--multi-arch", "all", *params, "oci:"+src+":latest", "docker://"+oci_ref], check=True)
