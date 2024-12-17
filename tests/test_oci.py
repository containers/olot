

from pathlib import Path

from pydantic import TypeAdapter

from olot.oci.oci_config import OCIManifestConfig
from olot.oci.oci_common import MediaType
from olot.oci.oci_image_index import OCIImageIndex
from olot.oci.oci_image_layout import OCIImageLayout
from olot.oci.oci_image_manifest import OCIImageManifest


def test_non_regression():
    """Given a known oci-layout, smoke test deserialization of OCI "models" 
    """
    base_path = Path(__file__).parent / "data" / "ocilayout1"
    with open(base_path / "oci-layout", "r") as f:
        m = OCIImageLayout.model_validate_json(f.read())
        print(m)
    with open(base_path / "index.json", "r") as f:
        m = OCIImageIndex.model_validate_json(f.read())
        print(m)
        print(m.manifests[0].size)
        print(m.model_dump_json(exclude_none=True))

    ta = TypeAdapter(MediaType)
    ta.validate_python("asd/asd")

    sha_path = base_path / "blobs" / "sha256"
    with open(sha_path / "db142d433cdde11f10ae479dbf92f3b13d693fd1c91053da9979728cceb1dc68", "r") as f:
        m = OCIImageIndex.model_validate_json(f.read())
        print(m)
        for manifest in m.manifests:
            print(manifest.platform)
            print(manifest.digest)

    with open(sha_path / "a3e1b257b47c09c9997212e53a0b570c1666501ad26e5bf33461304babab47c7", "r") as f:
        m = OCIImageManifest.model_validate_json(f.read())
        print(m)
        print(m.config.digest)

    with open(sha_path / "517b897a6a8312ce202a85c8a517d820b0fc5b6f5d14ec2a3267906f75680403", "r") as f:
        m = OCIManifestConfig.model_validate_json(f.read())
        print(m)
        print(m.rootfs)
        print(m.history)
