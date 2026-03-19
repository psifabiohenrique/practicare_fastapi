from dataclasses import dataclass
from typing import Any


@dataclass
class AIResult:
    """Standardized result from AI chain calls, including token usage."""

    content: Any
    input_tokens: int = 0
    output_tokens: int = 0
