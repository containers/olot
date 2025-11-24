import json
from typing import Union
from olot.oci.oci_common import MediaTypes
from olot.oci.oci_image_index import OCIImageIndex
from olot.oci.oci_image_manifest import ContentDescriptor, OCIImageManifest
from olot.utils.types import compute_hash_of_str


def get_descriptor_from_manifest(manifest: str) -> ContentDescriptor:
    """Given a manifest (RAW) return its descriptor
    
    Note: this MUST be the RAW content of the manifest in the repository/oci-layout so to compute the exact size in the descriptor.
    eg. use skopeo inspect --raw or oras manifest fetch (without --pretty)
    """    
    size = len(manifest)
    data = json.loads(manifest)
    model: Union[OCIImageManifest, OCIImageIndex]
    if data.get("mediaType") == MediaTypes.manifest:
        model = OCIImageManifest.model_validate_json(manifest)
    elif data.get("mediaType") == MediaTypes.index:
        model = OCIImageIndex.model_validate_json(manifest)
    if not model.mediaType:
        raise ValueError(f"Unexpected OCI manifest spec missing MediaType: {model}")
    result = ContentDescriptor(
        mediaType=model.mediaType,
        size=size,
        digest="sha256:" + compute_hash_of_str(manifest),
        artifactType=model.artifactType,
        urls=None,
        data=None,
    )
    return result
