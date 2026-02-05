from enum import Enum
from typing import Sequence


class CustomStrEnum(str, Enum):
    """To polyfill back to 3.9"""
    @classmethod
    def values(cls) -> Sequence[str]:
        return [e.value for e in cls]
    

class RemoveOriginals(CustomStrEnum):
    """Strategy to be applied when removing original files
    
    default: remove only model weights, configuration, etc.
    all: like default, but also remove the Model CarD"""
    DEFAULT = "default"
    ALL = "all"


class LayerInputType(CustomStrEnum):
    """has the layer been created from a file or a directory?"""
    FILE = "file"
    DIRECTORY = "directory"
