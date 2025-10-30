#!/usr/bin/env python3
"""
Test for Docker distribution manifest to OCI conversion.
"""

import json
from pathlib import Path
from pprint import pprint
import shutil

from olot.dockerdist.convert import convert_docker_manifests_to_oci
from olot.oci.oci_image_manifest import OCIImageManifest
from olot.oci.oci_common import MediaTypes
from tests.common import get_test_data_path


def test_convert_docker_manifest_to_oci(tmp_path: Path):
    """Test converting Docker distribution manifests to OCI format."""
    test_data_dir = get_test_data_path() / "dockerdist1"
    target_ocilayout = tmp_path / "myocilayout"
    shutil.copytree(test_data_dir, target_ocilayout)
    
    oci_manifests = convert_docker_manifests_to_oci(target_ocilayout)
    pprint(oci_manifests)
    expected_oci_manifests = {
        '52fd1a38c0cb8cb5669c172657a2f7316eb581fa263e6a72cee6cfa3c359d200': '52c14a52e8b62bbac09478f3f2fb71011c6afb2583ce763453193e6c4af62c7e',
        'a9421c2c6534fa90affb3526f9c79dd3c6ef86f2a9c8e0b39bc552174d6690ea': '475bc558e598b235b2be0cbdfee537df663f1b1960aada3232c3f35e2e6b9709'
        }
    assert oci_manifests == expected_oci_manifests


if __name__ == "__main__":
    test_convert_docker_manifest_to_oci()