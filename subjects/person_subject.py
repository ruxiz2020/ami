from dataclasses import dataclass
from typing import Dict, Literal

@dataclass
class PersonSubject:
    """
    Session-local description of WHO this record is about.
    This does NOT mean the person exists in the database.
    """
    subject_key: str            # e.g. "child_tmp_1"
    role: str                   # "child", "self", "parent", "other"
    descriptors: Dict[str, str] # name, dob, relation, approx_age, etc.
    confidence: float           # 0.0 – 1.0
    source: Literal["explicit", "inferred"]
