import json
from pathlib import Path
from typing import Dict, List
from olot.oci.oci_config import OCIManifestConfig
from olot.utils.types import compute_hash_of_str
from olot.oci.oci_image_manifest import OCIImageManifest, ContentDescriptor
from olot.oci.oci_common import MediaTypes

# Constants for media types
DOCKER_MANIFEST_V2 = "application/vnd.docker.distribution.manifest.v2+json"
DOCKER_LAYER_TAR_GZIP = "application/vnd.docker.image.rootfs.diff.tar.gzip"
DOCKER_CONFIG_V1 = "application/vnd.docker.container.image.v1+json"

def convert_docker_manifests_to_oci(directory: Path) -> Dict[str, OCIImageManifest]:
    """
    Scan directory for Docker distribution manifests and convert them to OCI format.
    
    Args:
        directory: Path to directory containing Docker distribution manifests
        
    Returns:
        OCIImageManifest: Converted OCI image manifest
        
    Raises:
        FileNotFoundError: If no Docker manifests are found
        ValueError: If manifest format is invalid or layers have wrong media type
    """
    manifest_files = []
    for blob in (directory / "blobs" / "sha256").iterdir():
        try:
            with open(blob, 'r') as f:
                data = json.load(f)
                if data.get("mediaType") == DOCKER_MANIFEST_V2:
                    manifest_files.append(blob)
        except (json.JSONDecodeError, KeyError):
            continue
    
    if not manifest_files:
        raise FileNotFoundError(f"No Docker distribution manifests found in {directory}")

    converted = {f.name: convert_docker_manifest_to_oci(f, directory) for f in manifest_files}
    return converted

def convert_docker_manifest_to_oci(manifest_file: Path, directory: Path) -> str:
    with open(manifest_file, 'r') as f:
        docker_manifest_data = json.load(f)

    if docker_manifest_data.get("mediaType") != DOCKER_MANIFEST_V2:
        raise ValueError(f"Expected {DOCKER_MANIFEST_V2}, got {docker_manifest_data.get('mediaType')}")

    oci_layers = []
    for layer in docker_manifest_data.get("layers", []):
        if layer.get("mediaType") != DOCKER_LAYER_TAR_GZIP:
            raise ValueError(f"Expected layer mediaType {DOCKER_LAYER_TAR_GZIP}, got {layer.get('mediaType')}")

        oci_layer = ContentDescriptor(
            mediaType=MediaTypes.layer_gzip,
            size=layer["size"],
            digest=layer["digest"]
        )
        oci_layers.append(oci_layer)

    config_descriptor = docker_manifest_data.get("config", {})
    if config_descriptor.get("mediaType") != DOCKER_CONFIG_V1:
        raise ValueError(f"Expected config mediaType {DOCKER_CONFIG_V1}, got {config_descriptor.get('mediaType')}")

    config_digest = config_descriptor["digest"]
    config_hash = config_digest.replace("sha256:", "")
    blobs_path = directory / "blobs" / "sha256"
    config_file = blobs_path / config_hash
    
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    with open(config_file, 'r') as f:
        docker_config_data = json.load(f)

    oci_config = OCIManifestConfig.model_validate(docker_config_data)
    
    oci_config_json = oci_config.model_dump_json(exclude_none=True)
    new_config_hash = compute_hash_of_str(oci_config_json)
    new_config_digest = f"sha256:{new_config_hash}"
    oci_config_descriptor = ContentDescriptor(
        mediaType=MediaTypes.config,
        size=len(oci_config_json.encode('utf-8')),
        digest=new_config_digest
    )
    (blobs_path / new_config_hash).write_text(oci_config_json)

    oci_manifest = OCIImageManifest(
        schemaVersion=2,
        mediaType=MediaTypes.manifest,
        config=oci_config_descriptor,
        layers=oci_layers
    )
    oci_manifest_json = oci_manifest.model_dump_json(exclude_none=True)
    oci_manifest_hash = compute_hash_of_str(oci_manifest_json)
    (blobs_path / oci_manifest_hash).write_text(oci_manifest_json)

    return oci_manifest_hash

