import hashlib
from typing import Annotated, Any

from pydantic import Field

NonEmptyString = Annotated[str, Field(..., pattern=r".{1,}")]
MapStringString = Annotated[dict[NonEmptyString, str], Field(...)]
MapStringObject = Annotated[dict[NonEmptyString, Any], Field(...)]

Int8 = Annotated[int, Field(ge=-128, le=127)]
Int64 = Annotated[int, Field(ge=-9223372036854776000, le=9223372036854776000)]
Base64 = Annotated[str, Field()]
Annotations = Annotated[MapStringString, Field()]

def compute_hash_of_str(content: str) -> str:
    h = hashlib.sha256()
    h.update(content.encode())
    return h.hexdigest()
