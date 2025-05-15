"""
Certificate schemas for validating certificate-related data.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Certificate schemas
class CertificateBase(BaseModel):
    """Base certificate schema with common attributes."""
    raspberry_uuid: str
    user_id: Optional[str] = None  # Optional when creating (can use currently authenticated user)

class CertificateCreate(CertificateBase):
    """Schema for creating a new certificate."""
    pass

class CertificateVerify(BaseModel):
    """Schema for verifying a certificate."""
    certificate_id: str

class CertificateResponse(CertificateBase):
    """Schema for certificate response data."""
    id: str
    timestamp: datetime
    verified: bool
    
    class Config:
        from_attributes = True
