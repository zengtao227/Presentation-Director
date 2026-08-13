"""Route-neutral presentation artifact capability vocabulary."""

from enum import Enum
from typing import Literal

CAPABILITY_VOCABULARY_ID: Literal["presentation-artifact-capabilities"] = "presentation-artifact-capabilities"
CAPABILITY_VOCABULARY_VERSION: Literal["1.0.0"] = "1.0.0"


class PresentationCapability(str, Enum):
    EDITABLE_TEXT = "editable_text"
    NATIVE_TABLE = "native_table"
    NATIVE_CHART = "native_chart"
    EDITABLE_CHART_DATA = "editable_chart_data"
    NATIVE_SHAPES = "native_shapes"
    ATTACHED_CONNECTORS = "attached_connectors"
    SPEAKER_NOTES = "speaker_notes"
    EMBEDDED_IMAGES = "embedded_images"
