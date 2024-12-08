
from typing import Annotated, Any, Dict, List
from pydantic import AnyUrl, Field

MediaType = Annotated[str, Field(
        ...,
        pattern=r'^[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}/[A-Za-z0-9][A-Za-z0-9!#$&^_.+-]{0,126}$'
    )]


Digest = Annotated[str, Field(
        ...,
        pattern=r'^[a-z0-9]+(?:[+._-][a-z0-9]+)*:[a-zA-Z0-9=_-]+$',
        description="the cryptographic checksum digest of the object, in the pattern '<algorithm>:<encoded>'",
    )]


Urls = Annotated[List[AnyUrl],Field(
        ..., description='a list of urls from which this object may be downloaded'
    )]


NonEmptyString = Annotated[str, Field(..., pattern=r".{1,}")]


MapStringString = Annotated[Dict[NonEmptyString, str], Field(...)]


MapStringObject = Annotated[Dict[NonEmptyString, Any], Field(...)]


Int8 = Annotated[int, Field(ge=-128, le=127)]


Int64 = Annotated[int, Field(ge=-9223372036854776000, le=9223372036854776000)]


Base64 = Annotated[str, Field()]


Annotations = Annotated[MapStringString, Field()]
