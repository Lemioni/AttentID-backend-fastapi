"""
Certificate service module for handling certificate operations.
"""

import uuid
import hashlib
import hmac
import base64
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.models import User, Certificate
from app.config.settings import settings

def generate_signature(certificate_id: str, user_id: str, raspberry_uuid: str, timestamp: datetime) -> str:
    """
    Generate a digital signature for certificate verification.
    Uses HMAC with SHA-256 for creating a secure signature.
    
    Args:
        certificate_id (str): Certificate ID
        user_id (str): User ID
        raspberry_uuid (str): Raspberry Pi UUID
        timestamp (datetime): Certificate issue timestamp
    
    Returns:
        str: Base64-encoded signature
    """
    # Create a message string with all the certificate data
    msg = f"{certificate_id}:{user_id}:{raspberry_uuid}:{timestamp.isoformat()}"
    
    # Create signature using HMAC-SHA256 with app secret key
    digest = hmac.new(
        settings.SECRET_KEY.encode(),
        msg.encode(), 
        hashlib.sha256
    ).digest()
    
    # Return base64 encoded signature
    return base64.b64encode(digest).decode()

def create_certificate(db: Session, user_id: str, raspberry_uuid: str) -> Certificate:
    """
    Create a new attendance certificate.
    
    Args:
        db (Session): Database session
        user_id (str): ID of the user who was present
        raspberry_uuid (str): UUID of the Raspberry Pi that detected the user
    
    Returns:
        Certificate: The created certificate
    """
    # Check if the user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )
    
    # Generate certificate ID with prefix
    certificate_id = f"cert-{uuid.uuid4()}"
    
    # Create timestamp
    timestamp = datetime.now()
    
    # Generate signature
    signature = generate_signature(certificate_id, user_id, raspberry_uuid, timestamp)
    
    # Create certificate
    certificate = Certificate(
        id=certificate_id,
        user_id=user_id,
        raspberry_uuid=raspberry_uuid,
        timestamp=timestamp,
        signature=signature,
        verified=False
    )
    
    # Save to database
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    
    return certificate

def get_certificate(db: Session, certificate_id: str) -> Optional[Certificate]:
    """
    Get a certificate by ID.
    
    Args:
        db (Session): Database session
        certificate_id (str): Certificate ID
    
    Returns:
        Optional[Certificate]: The certificate if found, None otherwise
    """
    return db.query(Certificate).filter(Certificate.id == certificate_id).first()

def verify_certificate(db: Session, certificate_id: str) -> Certificate:
    """
    Verify a certificate's authenticity.
    
    Args:
        db (Session): Database session
        certificate_id (str): Certificate ID to verify
    
    Returns:
        Certificate: The verified certificate
        
    Raises:
        HTTPException: If the certificate doesn't exist or has been tampered with
    """
    # Get the certificate
    certificate = get_certificate(db, certificate_id)
    
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID {certificate_id} not found"
        )
    
    # Generate signature from current certificate data
    current_signature = generate_signature(
        certificate.id, 
        certificate.user_id, 
        certificate.raspberry_uuid, 
        certificate.timestamp
    )
    
    # Compare with stored signature
    if current_signature != certificate.signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certificate has been tampered with and is not valid"
        )
    
    # Mark as verified
    certificate.verified = True
    db.commit()
    db.refresh(certificate)
    
    return certificate

def get_user_certificates(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[Certificate]:
    """
    Get all certificates for a specific user.
    
    Args:
        db (Session): Database session
        user_id (str): User ID
        skip (int): Number of records to skip
        limit (int): Maximum number of records to return
    
    Returns:
        List[Certificate]: List of certificates
    """
    return db.query(Certificate).filter(Certificate.user_id == user_id).offset(skip).limit(limit).all()
