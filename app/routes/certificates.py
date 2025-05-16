"""
Certificate routes for handling certificate generation and verification.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
from typing import List, Optional

from app.models.models import User, Certificate
from app.schemas.schemas import CertificateCreate, CertificateResponse, CertificateVerify
from app.services.certificates import create_certificate, verify_certificate, get_certificate, get_user_certificates
from app.services.auth import get_current_active_user
from app.core.database import get_db

router = APIRouter(
    prefix="/certificates", 
    tags=["Certificates"]
)

@router.post(
    "", 
    response_model=CertificateResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new attendance certificate",
    description="Creates a certificate proving a user's presence at a specific location (Raspberry Pi). "
                "Verifies actual presence using MQTT checkpoint records before issuing certificate."
)
async def create_attendance_certificate(
    certificate_data: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new certificate of attendance for a user at a specific location (Raspberry Pi).
    Verifies the user was actually present by checking MQTT records from checkpoints.
    
    Args:
        certificate_data: Certificate data including Raspberry Pi UUID, optional timestamp, and time window
        db: Database session
        current_user: Currently authenticated user
        
    Returns:
        The created certificate
        
    Raises:
        HTTPException 400: If no verification records exist proving the user was present
        HTTPException 404: If the user doesn't exist
    """
    # Use current user's ID if not provided
    user_id = certificate_data.user_id or current_user.id
    
    # Create certificate with time window from the request body
    certificate = create_certificate(
        db=db,
        user_id=user_id,
        raspberry_uuid=certificate_data.raspberry_uuid,
        timestamp=certificate_data.timestamp,
        time_window_minutes=certificate_data.time_window_minutes
    )
    
    return certificate

@router.get(
    "", 
    response_model=List[CertificateResponse],
    summary="Get user certificates",
    description="Retrieve all certificates for the current user."
)
async def get_user_attendance_certificates(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all certificates for the current user.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Currently authenticated user
        
    Returns:
        List of certificates
    """
    return get_user_certificates(db, current_user.id, skip, limit)

@router.get(
    "/all",
    response_model=List[CertificateResponse],
    summary="Get all certificates in system",
    description="Admin endpoint to retrieve all certificates in the system."
)
async def get_all_certificates(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all certificates in the system (admin only).
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        db: Database session
        current_user: Currently authenticated user
        
    Returns:
        List of certificates
    """
    # Check if user has admin role by checking user roles
    from app.services.auth import get_user_roles
    
    user_roles = get_user_roles(db, current_user.id)
    
    # Check if the user has admin role (ID 2)
    if 2 not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access all certificates"
        )
    
    certificates = db.query(Certificate).offset(skip).limit(limit).all()
    return certificates

@router.get(
    "/{certificate_id}", 
    response_model=CertificateResponse,
    summary="Get certificate details",
    description="Get details of a specific certificate."
)
async def get_certificate_details(
    certificate_id: str = Path(..., description="ID of the certificate to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get details of a specific certificate.
    
    Args:
        certificate_id: Certificate ID
        db: Database session
        current_user: Currently authenticated user
        
    Returns:
        Certificate details
    """
    certificate = get_certificate(db, certificate_id)
    
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID {certificate_id} not found"
        )
        
    return certificate

@router.post(
    "/verify",
    response_model=CertificateResponse,
    summary="Verify certificate authenticity",
    description="Verifies that a certificate is authentic and has not been tampered with."
)
async def verify_certificate_authenticity(
    verify_data: CertificateVerify,
    db: Session = Depends(get_db)
):
    """
    Verify a certificate's authenticity.
    
    Args:
        verify_data: Certificate verification data
        db: Database session
        
    Returns:
        Verified certificate details
    """
    certificate = verify_certificate(db, verify_data.certificate_id)
    return certificate

@router.get("/debug_presence/{raspberry_uuid}/{user_id}", response_model=dict)
async def debug_presence_verification(
    raspberry_uuid: str,
    user_id: str,
    timestamp: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """Debug endpoint to check MQTT entries for a user at a location"""
    # First query to find entries with raspberry UUID
    rasp_query = """
        SELECT topic, payload, time
        FROM mqttenteries 
        WHERE topic LIKE :rasp_pattern
    """
    
    rasp_pattern = f"%{raspberry_uuid}%"
    rasp_results = db.execute(text(rasp_query), {"rasp_pattern": rasp_pattern}).fetchall()
    
    # Second query to find entries with user ID
    user_query = """
        SELECT topic, payload, time
        FROM mqttenteries 
        WHERE topic LIKE :user_pattern
    """
    
    user_pattern = f"%{user_id}%"
    user_results = db.execute(text(user_query), {"user_pattern": user_pattern}).fetchall()
    
    # Third query to find entries with both
    combined_query = """
        SELECT topic, payload, time
        FROM mqttenteries 
        WHERE topic LIKE :combined_pattern
    """
    
    combined_pattern = f"%{raspberry_uuid}%{user_id}%"
    combined_results = db.execute(text(combined_query), {"combined_pattern": combined_pattern}).fetchall()
    
    return {
        "raspberry_uuid": raspberry_uuid,
        "user_id": user_id,
        "timestamp": timestamp,
        "rasp_pattern": rasp_pattern,
        "rasp_entries_count": len(rasp_results),
        "rasp_entries": [{"topic": row[0], "payload": row[1], "time": row[2]} for row in rasp_results[:5]],
        "user_pattern": user_pattern,
        "user_entries_count": len(user_results),
        "user_entries": [{"topic": row[0], "payload": row[1], "time": row[2]} for row in user_results[:5]],
        "combined_pattern": combined_pattern,
        "combined_entries_count": len(combined_results),
        "combined_entries": [{"topic": row[0], "payload": row[1], "time": row[2]} for row in combined_results]
    }