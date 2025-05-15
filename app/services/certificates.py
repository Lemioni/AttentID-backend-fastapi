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

def verify_user_presence(db: Session, user_id: str, raspberry_uuid: str, timestamp: Optional[datetime] = None, time_window_minutes: int = 30) -> bool:
    """
    Verify that the user was actually present at the specified location by checking MQTT entries.
    Looks for MQTT topics with the pattern related to user detection at a specific location.
    
    Args:
        db (Session): Database session
        user_id (str): ID of the user to verify
        raspberry_uuid (str): UUID of the Raspberry Pi location
        timestamp (Optional[datetime]): Optional timestamp for checking presence at a specific time
        time_window_minutes (int): Time window in minutes to search around the provided timestamp (±minutes)
    
    Returns:
        bool: True if user presence is confirmed, False otherwise
    """
    # First try to find entries with both IDs
    direct_query = """
        SELECT * FROM mqttenteries 
        WHERE topic LIKE :topic_pattern
    """
    
    # Add time constraints if timestamp was provided
    if timestamp:
        # Look for entries within specified time window from the timestamp
        time_from = timestamp - timedelta(minutes=time_window_minutes)
        time_to = timestamp + timedelta(minutes=time_window_minutes)
        direct_query += " AND time BETWEEN :time_from AND :time_to"
    
    # Build the topic pattern to search for both IDs
    topic_pattern = f"%{raspberry_uuid}%{user_id}%"
    
    # Execute the query
    params = {"topic_pattern": topic_pattern}
    if timestamp:
        params.update({"time_from": time_from, "time_to": time_to})
    
    result = db.execute(text(direct_query), params).fetchall()
    
    print(f"Looking for direct match with pattern: {topic_pattern}")
    print(f"Found {len(result)} matching entries")
    
    # If direct match found, return True
    if len(result) > 0:
        return True
    
    # If no direct match, try alternate approaches for more flexibility
    
    # Try to match just with user ID and extract Raspberry UUID from topic
    user_query = """
        SELECT topic, payload, time FROM mqttenteries 
        WHERE topic LIKE :user_pattern
    """
    
    if timestamp:
        user_query += " AND time BETWEEN :time_from AND :time_to"
    
    user_pattern = f"%{user_id}%"
    
    params = {"user_pattern": user_pattern}
    if timestamp:
        params.update({"time_from": time_from, "time_to": time_to})
    
    user_results = db.execute(text(user_query), params).fetchall()
    
    print(f"Looking for user entries with pattern: {user_pattern}")
    print(f"Found {len(user_results)} user entries")
    
    # Extract UUIDs from topics and check for matches
    for row in user_results:
        topic = row[0]
        parts = topic.split('/')
        
        # Look for UUID-like parts
        for part in parts:
            if len(part) > 30 and '-' in part:
                # Check if it's similar to our raspberry UUID
                if raspberry_uuid in part or part in raspberry_uuid:
                    print(f"Found matching UUID in topic: {part}")
                    return True
                
                # Check suffix matches (last 8 chars)
                if len(part) >= 8 and len(raspberry_uuid) >= 8:
                    if part[-8:] == raspberry_uuid[-8:]:
                        print(f"Found suffix match: {part[-8:]} == {raspberry_uuid[-8:]}")
                        return True
    
    # No matches found
    print("No matches found with any method")
    return False

def create_certificate(db: Session, user_id: str, raspberry_uuid: str, timestamp: Optional[datetime] = None, time_window_minutes: int = 30) -> Certificate:
    """
    Create a new attendance certificate.
    
    Args:
        db (Session): Database session
        user_id (str): ID of the user who was present
        raspberry_uuid (str): UUID of the Raspberry Pi that detected the user
        timestamp (Optional[datetime]): Optional timestamp for checking presence at a specific time
        time_window_minutes (int): Time window in minutes to search around the provided timestamp (±minutes)
    
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
    if not verify_user_presence(db, user_id, raspberry_uuid, timestamp, time_window_minutes):
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
