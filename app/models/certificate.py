"""
Model for attendance certificates.
"""

import uuid
from sqlalchemy import Column, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Certificate(Base):
    """
    Model representing attendance certificates in the system.
    Stores certificate information including user ID, location (raspberry ID), and timestamp.
    """
    __tablename__ = "certificates"
    
    id = Column(String, primary_key=True, default=lambda: f"cert-{uuid.uuid4()}")  # Primary key with cert- prefix
    user_id = Column(String, ForeignKey("users.id"))  # User who received the certificate
    raspberry_uuid = Column(String)  # Location identifier (Raspberry Pi UUID)
    timestamp = Column(DateTime, default=datetime.now)  # When the certificate was issued
    verified = Column(Boolean, default=False)  # Whether the certificate has been verified
    signature = Column(Text)  # Digital signature for verification
    
    # Relationship
    user = relationship("User", back_populates="certificates")
