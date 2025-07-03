from pathlib import Path
import pathlib
import shutil
import subprocess
import typing
import os


ODH_MODELCAR_BASE_IMAGE = "quay.io/opendatahub/odh-modelcar-base-image:d59dabeedfbfca18eeeb6e24ea99700b46e163dc"
EMBEDDED_OCI_LAYOUT_DIR = "embedded_oci_layout"


def copy_base_image_to_oci_layout(base_image: str, dest: typing.Union[str, os.PathLike]):
    """
    Copy a base image to OCI layout using skopeo.
    
    Args:
        base_image: The source base image reference
        dest: The destination OCI layout directory
    
    Returns:
        The result of the subprocess.run call
    """
    if isinstance(dest, os.PathLike):
        dest = str(dest)
    return subprocess.run(["skopeo", "copy", "--multi-arch", "all", "docker://"+base_image, "oci:"+dest+":latest"], check=True)


def embedded_oci_layout(
    target_path: typing.Union[str, os.PathLike]
) -> None:
    """
    Create an oci-layout from the embedded modelcar base image.
    The embedded modelcar base image is sourced from the ODH_MODELCAR_BASE_IMAGE constant.
    
    Args:
        typing.Union[str, os.PathLike]: Directory where the oci-layout will be created
    """
    import olot
    package_root = Path(olot.__file__).parent  # olot/ directory in installed package
    embedded_path = package_root / EMBEDDED_OCI_LAYOUT_DIR
    
    if not embedded_path.exists():
        raise FileNotFoundError(f"Embedded data directory {embedded_path} not found")
    
    target_path = pathlib.Path(target_path).expanduser().resolve()
    target_path.mkdir(parents=True, exist_ok=True)
    shutil.copytree(embedded_path, target_path, dirs_exist_ok=True)


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dest_dir = os.path.join(current_dir, EMBEDDED_OCI_LAYOUT_DIR)
    
    os.makedirs(dest_dir, exist_ok=True)
    
    print(f"Copying {ODH_MODELCAR_BASE_IMAGE} to OCI layout at {dest_dir}")
    try:
        result = copy_base_image_to_oci_layout(ODH_MODELCAR_BASE_IMAGE, dest_dir)
        print(f"Successfully copied image to {dest_dir}")
        print(f"Command completed with return code: {result.returncode}")
    except subprocess.CalledProcessError as e:
        print(f"Error copying image: {e}")
        exit(1)
