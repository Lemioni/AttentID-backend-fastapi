"""
Certificate service module for handling certificate operations.
"""

import uuid
import hashlib
import hmac
import base64
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException, status

from app.models.models import User, Certificate, MQTTEntry
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

def verify_user_presence(db: Session, user_id: str, raspberry_uuid: str, timestamp: Optional[datetime] = None) -> bool:
    """
    Verify that the user was actually present at the specified location by checking MQTT entries.
    Looks for MQTT topics with the pattern 'ble_devices/{raspberry_uuid}/*/overenaadresa*/{user_uuid}'
    
    Args:
        db (Session): Database session
        user_id (str): ID of the user to verify
        raspberry_uuid (str): UUID of the Raspberry Pi location
        timestamp (Optional[datetime]): Optional timestamp for checking presence at a specific time
    
    Returns:
        bool: True if user presence is confirmed, False otherwise
    """
    
    # Extract user UUID without prefix if it has one
    user_uuid = user_id
    if "-" in user_id:
        user_uuid = user_id.split("-", 1)[1]
    
    # Build the search query
    query = """
        SELECT * FROM mqttenteries 
        WHERE topic LIKE :topic_pattern
    """
    
    # Add time constraints if timestamp was provided
    if timestamp:
        # Look for entries within +/- 1 hour from specified time
        time_from = timestamp - timedelta(hours=1)
        time_to = timestamp + timedelta(hours=1)
        query += " AND time BETWEEN :time_from AND :time_to"
    
    # Build the topic pattern to search for - making it more flexible
    topic_pattern = f"%{raspberry_uuid}%{user_id}%"    
    # Execute the query with logging for debugging
    params = {"topic_pattern": topic_pattern}
    if timestamp:
        params.update({"time_from": time_from, "time_to": time_to})
    
    result = db.execute(text(query), params).fetchall()
    
    # For debugging - log what we're looking for and what we found
    print(f"Looking for topic pattern: {topic_pattern}")
    print(f"Found {len(result)} matching entries")
    
    # Return True if any matching entries were found
    return len(result) > 0

def create_certificate(db: Session, user_id: str, raspberry_uuid: str, timestamp: Optional[datetime] = None) -> Certificate:
    """
    Create a new attendance certificate.
    
    Args:
        db (Session): Database session
        user_id (str): ID of the user who was present
        raspberry_uuid (str): UUID of the Raspberry Pi that detected the user
        timestamp (Optional[datetime]): Optional timestamp for checking presence at a specific time
    
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
    
    # Verify that the user was actually present at this location
    if not verify_user_presence(db, user_id, raspberry_uuid, timestamp):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate certificate: No verification found that the user was present at this location"
        )
    
    # Generate certificate ID with prefix
    certificate_id = f"cert-{uuid.uuid4()}"
    
    # Create timestamp - use provided timestamp or current time
    cert_timestamp = timestamp if timestamp else datetime.now()
    
    # Generate signature
    signature = generate_signature(certificate_id, user_id, raspberry_uuid, cert_timestamp)
      # Create certificate
    certificate = Certificate(
        id=certificate_id,
        user_id=user_id,
        raspberry_uuid=raspberry_uuid,
        timestamp=cert_timestamp,  # Using the timestamp we determined earlier
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
