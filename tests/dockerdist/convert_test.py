#!/usr/bin/env python3
"""
Test for Docker distribution manifest to OCI conversion.
"""

import json
from pathlib import Path
from pprint import pprint

from olot.dockerdist.convert import convert_docker_manifests_to_oci
from olot.oci.oci_image_manifest import OCIImageManifest
from olot.oci.oci_common import MediaTypes
from tests.common import get_test_data_path


def test_convert_docker_manifest_to_oci():
    """Test converting Docker distribution manifests to OCI format."""
    test_data_dir = get_test_data_path() / "dockerdist1"
    
    oci_manifests = convert_docker_manifests_to_oci(test_data_dir)
    pprint(oci_manifests)


if __name__ == "__main__":
    test_convert_docker_manifest_to_oci()