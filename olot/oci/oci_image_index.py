# generated by datamodel-codegen:
#   filename:  image-index-schema.json
#   timestamp: 2024-12-04T08:16:48+00:00

from __future__ import annotations

from typing import Annotated, List, Optional
from pathlib import Path

from pydantic import BaseModel, Field

from olot.oci.oci_common import MediaTypes, MediaType, Digest, Urls
from olot.utils.types import  Int64, Base64, Annotations

class Platform(BaseModel):
    architecture: str
    os: str
    os_version: Optional[str] = Field(None, alias='os.version')
    os_features: Optional[List[str]] = Field(None, alias='os.features')
    variant: Optional[str] = None


# class MediaType(BaseModel):
#     __root__: constr(
#         regex=r'^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$'
#     )
# class MediaType(RootModel[str]):
#     root: str = Field(
#         ...,
#         pattern=r'^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$'
#     )


# class Digest(BaseModel):
#     __root__: constr(regex=r'^[a-z0-9]+(?:[+._-][a-z0-9]+)*:[a-zA-Z0-9=_-]+$') = Field(
#         ...,
#         description="the cryptographic checksum digest of the object, in the pattern '<algorithm>:<encoded>'",
#     )
# class Digest(RootModel[str]):
#     root: str = Field(
#         ...,
#         pattern=r'^[a-z0-9]+(?:[+._-][a-z0-9]+)*:[a-zA-Z0-9=_-]+$',
#         description="the cryptographic checksum digest of the object, in the pattern '<algorithm>:<encoded>'",
#     )


# class Urls(BaseModel):
#     __root__: List[AnyUrl] = Field(
#         ..., description='a list of urls from which this object may be downloaded'
#     )
# class Urls(RootModel[List[AnyUrl]]):
#     root: List[AnyUrl] = Field(
#         ..., description='a list of urls from which this object may be downloaded'
#     )


# class MapStringString(BaseModel):
#     __root__: Dict[constr(regex=r'.{1,}'), str]
# class MapStringString(RootModel[Dict[constr(pattern=r".{1,}"), str]]):
#     """
#     A Pydantic RootModel for a dictionary where keys are non-empty strings
#     and values are strings.
#     """
#     root: Dict[constr(pattern=r".{1,}"), str] = Field(
#         ...,
#         description="A dictionary where keys are non-empty strings and values are strings."
#     )


# class Int8(BaseModel):
#     __root__: conint(ge=-128, le=127)
# class Int8(RootModel[conint(ge=-128, le=127)]):
#     root: conint(ge=-128, le=127) = Field(
#         ...,
#         description="An integer constrained to the 8-bit signed range (-128 to 127)."
#     )


# class Int16(BaseModel):
#     __root__: conint(ge=-32768, le=32767)


# class Int32(BaseModel):
#     __root__: conint(ge=-2147483648, le=2147483647)


# class Int64(BaseModel):
#     __root__: conint(ge=-9223372036854776000, le=9223372036854776000)
# class Int64(RootModel[int]):
#     root: int = Field(
#         ...,
#         ge=-9223372036854776000,
#         le=9223372036854776000,
#     )

# class Uint8(BaseModel):
#     __root__: conint(ge=0, le=255)


# class Uint16(BaseModel):
#     __root__: conint(ge=0, le=65535)


# class Uint32(BaseModel):
#     __root__: conint(ge=0, le=4294967295)


# class Uint64(BaseModel):
#     __root__: conint(ge=0, le=18446744073709552000)
# class Uint64(RootModel[int]):
#     root: int = Field(
#         ...,
#         ge=0,
#         le=18446744073709552000,
#     )


# class Uint16Pointer(BaseModel):
#     __root__: Optional[Uint16]


# class Uint64Pointer(BaseModel):
#     __root__: Optional[Uint64]


# class Base64(RootModel[str]):
#     pass


# class StringPointer(BaseModel):
#     __root__: Optional[str]


# class MapStringObject(BaseModel):
#     __root__: Dict[constr(regex=r'.{1,}'), Dict[str, Any]]


# class Annotations(BaseModel):
#     __root__: MapStringString
# class Annotations(RootModel[MapStringString]):
#     pass


class ContentDescriptor(BaseModel):
    mediaType: MediaType = Field(
        ..., description='the mediatype of the referenced object'
    )
    size: Int64 = Field(..., description='the size in bytes of the referenced object')
    digest: Digest = Field(
        ...,
        description="the cryptographic checksum digest of the object, in the pattern '<algorithm>:<encoded>'",
    )
    urls: Optional[Urls] = Field(
        None, description='a list of urls from which this object may be downloaded'
    )
    data: Optional[Base64] = Field(
        None, description='an embedding of the targeted content (base64 encoded)'
    )
    artifactType: Optional[MediaType] = Field(
        None, description='the IANA media type of this artifact'
    )
    annotations: Optional[Annotations] = None


class Manifest(BaseModel):
    mediaType: MediaType = Field(
        ..., description='the mediatype of the referenced object'
    )
    size: Int64 = Field(..., description='the size in bytes of the referenced object')
    digest: Digest = Field(
        ...,
        description="the cryptographic checksum digest of the object, in the pattern '<algorithm>:<encoded>'",
    )
    urls: Optional[Urls] = Field(
        None, description='a list of urls from which this object may be downloaded'
    )
    platform: Optional[Platform] = None
    annotations: Optional[Annotations] = None


class OCIImageIndex(BaseModel):
    schemaVersion: Annotated[int, Field(ge=2, le=2)] = Field(
        ...,
        description='This field specifies the image index schema version as an integer',
    )
    mediaType: Optional[MediaType] = Field(
        None, description='the mediatype of the referenced object'
    )
    artifactType: Optional[MediaType] = Field(
        None, description='the artifact mediatype of the referenced object'
    )
    subject: Optional[ContentDescriptor] = None
    manifests: List[Manifest]
    annotations: Optional[Annotations] = None


def read_ocilayout_root_index(ocilayout: Path) -> OCIImageIndex:
    ocilayout_root_index = None
    with open(ocilayout / "index.json", "r") as f:
        ocilayout_root_index = OCIImageIndex.model_validate_json(f.read())
    return ocilayout_root_index


def create_oci_image_index(
    schemaVersion: int = 2,
    mediaType: Optional[str] = MediaTypes.index,
    artifactType: Optional[str] = None,
    subject: Optional[ContentDescriptor] = None,
    manifests: List[Manifest] = [],
    annotations: Optional[Annotations] = None
) -> OCIImageIndex:
    """
    Create an OCI image index object.
    """
    return OCIImageIndex(
        schemaVersion=schemaVersion,
        mediaType=mediaType,
        artifactType=artifactType,
        subject=subject,
        manifests=manifests,
        annotations=annotations
    )