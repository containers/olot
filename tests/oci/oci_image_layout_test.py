import pytest
from olot.oci.oci_image_layout import verify_ocilayout

from tests.common import test_data_path

def test_verify_ocilayout():
    """Test verify_ocilayout() fn on known oci-layout and not
    """
    data_path = test_data_path()
    verify_ocilayout(data_path / "ocilayout1")
    verify_ocilayout(data_path / "ocilayout2")
    verify_ocilayout(data_path / "ocilayout3")
    with pytest.raises(Exception):
        verify_ocilayout(data_path)
