#!/usr/bin/env python3
"""
Test for Docker distribution manifest to OCI conversion.
"""

import json
from pathlib import Path

from olot.oci.oci_image_manifest import convert_docker_manifest_to_oci, OCIImageManifest
from olot.oci.oci_common import MediaTypes


def test_convert_docker_manifest_to_oci():
    """Test converting Docker distribution manifest to OCI format."""
    # Use the test data directory
    test_data_dir = Path(__file__).parent.parent / "data" / "dockerdist1"
    
    # Convert Docker manifest to OCI
    oci_manifest = convert_docker_manifest_to_oci(test_data_dir)
    
    # Verify it's a valid OCI manifest
    assert isinstance(oci_manifest, OCIImageManifest)
    assert oci_manifest.schemaVersion == 2
    assert oci_manifest.mediaType == MediaTypes.manifest
    
    # Verify config descriptor
    assert oci_manifest.config.mediaType == "application/vnd.oci.image.config.v1+json"
    assert oci_manifest.config.digest.startswith("sha256:")
    assert oci_manifest.config.size > 0
    
    # Verify layers are converted to OCI format
    assert len(oci_manifest.layers) > 0
    for layer in oci_manifest.layers:
        assert layer.mediaType == "application/vnd.oci.image.layer.v1.tar+gzip"
        assert layer.digest.startswith("sha256:")
        assert layer.size > 0
    
    print("✓ Docker manifest conversion test passed!")
    print(f"  - Schema version: {oci_manifest.schemaVersion}")
    print(f"  - Media type: {oci_manifest.mediaType}")
    print(f"  - Config digest: {oci_manifest.config.digest}")
    print(f"  - Number of layers: {len(oci_manifest.layers)}")
    print(f"  - Layer media types: {[layer.mediaType for layer in oci_manifest.layers]}")


if __name__ == "__main__":
    test_convert_docker_manifest_to_oci()