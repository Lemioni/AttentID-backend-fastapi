"""
Certificate routes for handling certificate generation and verification.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from typing import List

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
    description="Creates a certificate proving a user's presence at a specific location (Raspberry Pi)."
)
async def create_attendance_certificate(
    certificate_data: CertificateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a new certificate of attendance for a user at a specific location (Raspberry Pi).
    
    Args:
        certificate_data: Certificate data including Raspberry Pi UUID
        db: Database session
        current_user: Currently authenticated user
        
    Returns:
        The created certificate
    """
    # Use current user's ID if not provided
    user_id = certificate_data.user_id or current_user.id
    
    # Create certificate
    certificate = create_certificate(db, user_id, certificate_data.raspberry_uuid)
    
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
