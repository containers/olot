
from typing import Annotated, List
from pydantic import AnyUrl, Field


MediaType = Annotated[str, Field(
        ...,
        pattern=r'^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$'
    )]

class MediaTypes:
    manifest: MediaType = "application/vnd.oci.image.manifest.v1+json"
    index: MediaType = "application/vnd.oci.image.index.v1+json"
    layer: MediaType = "application/vnd.oci.image.layer.v1.tar"
    layer_gzip: MediaType = "application/vnd.oci.image.layer.v1.tar+gzip"


Digest = Annotated[str, Field(
        ...,
        pattern=r'^[a-z0-9]+(?:[+._-][a-z0-9]+)*:[a-zA-Z0-9=_-]+$',
        description="the cryptographic checksum digest of the object, in the pattern '<algorithm>:<encoded>'",
    )]


Urls = Annotated[List[AnyUrl],Field(
        ..., description='a list of urls from which this object may be downloaded'
    )]



