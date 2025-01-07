
from typing import Annotated, List
from pydantic import AnyUrl, Field


MediaType = Annotated[str, Field(
        ...,
        pattern=r'^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$'
    )]


class Keys:
        image_title_annotation = "org.opencontainers.image.title"
        image_created_annotation = "org.opencontainers.image.created"

class Values:
        empty_digest = "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
        empty_data = "e30="

class MediaTypes:
        """Constant values from OCI Image Manifest spec

        See also: https://github.com/opencontainers/image-spec/blob/main/media-types.md
        """
        manifest: MediaType = "application/vnd.oci.image.manifest.v1+json"
        index: MediaType = "application/vnd.oci.image.index.v1+json"
        layer: MediaType = "application/vnd.oci.image.layer.v1.tar"
        layer_gzip: MediaType = "application/vnd.oci.image.layer.v1.tar+gzip"
        empty: MediaType = "application/vnd.oci.empty.v1+json"
        config: MediaType = "application/vnd.oci.image.config.v1+json"

Digest = Annotated[str, Field(
        ...,
        pattern=r'^[a-z0-9]+(?:[+._-][a-z0-9]+)*:[a-zA-Z0-9=_-]+$',
        description="the cryptographic checksum digest of the object, in the pattern '<algorithm>:<encoded>'",
    )]


Urls = Annotated[List[AnyUrl],Field(
        ..., description='a list of urls from which this object may be downloaded'
    )]


