from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

class DocumentStatus(str, Enum):
    PROCESSED = "PROCESSED"
    FLAGGED = "FLAGGED"
    FAILED = "FAILED"

class ExtractedData(BaseModel):
    doc_type: Optional[str] = None
    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    id_number: Optional[str] = None
    nationality: Optional[str] = None
    expiry_date: Optional[str] = None
    ocr_confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    
class DocumentData(ExtractedData):
    drive_file_id: str
    file_hash: Optional[str] = None
    status: Optional[DocumentStatus] = None
    field_completeness: float = Field(default=0.0, ge=0.0, le=100.0)
    combined_score: float = Field(default=0.0, ge=0.0, le=100.0)
    is_expired: bool = False
    validation_errors: List[str] = Field(default_factory=list)
