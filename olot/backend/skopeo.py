import os
import shutil
import subprocess
import typing

def is_skopeo() -> bool :
    return shutil.which("skopeo") is not None

def skopeo_pull(base_image: str, dest: typing.Union[str, os.PathLike]):
    if isinstance(dest, os.PathLike):
        dest = str(dest)
    return subprocess.run(["skopeo", "copy", "--multi-arch", "all", "docker://"+base_image, "oci:"+dest+":latest"], check=True)
