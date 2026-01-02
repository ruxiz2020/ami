from dataclasses import dataclass
from typing import Literal

@dataclass
class DomainSubject:
    """
    Describes WHAT area of life this record belongs to.
    This is NOT agent-specific logic.
    This is pure data.
    """
    domain: str                 # e.g. "healthcare", "child", "learning"
    subdomain: str              # e.g. "medical_check", "language", "technical"
    confidence: float           # 0.0 – 1.0
    source: Literal["explicit", "inferred"]
