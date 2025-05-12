from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.models import Location, LocationType
from app.schemas.schemas import Location as LocationSchema, LocationCreate, LocationType as LocationTypeSchema, LocationTypeCreate

router = APIRouter()

@router.post("/type", response_model=LocationTypeSchema, status_code=status.HTTP_201_CREATED)
def create_location_type(location_type: LocationTypeCreate, db: Session = Depends(get_db)):
    """
    Create a new location type
    """
    # Check if location type with same name already exists
    db_location_type = db.query(LocationType).filter(LocationType.name == location_type.name).first()
    if db_location_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Location type with name '{location_type.name}' already exists"
        )
    
    # Create new location type
    new_location_type = LocationType(
        name=location_type.name,
        description=location_type.description
    )
    
    db.add(new_location_type)
    db.commit()
    db.refresh(new_location_type)
    
    return new_location_type

@router.get("/types", response_model=List[LocationTypeSchema])
def get_location_types(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get all location types
    """
    location_types = db.query(LocationType).offset(skip).limit(limit).all()
    return location_types

@router.post("/", response_model=LocationSchema, status_code=status.HTTP_201_CREATED)
def create_location(location: LocationCreate, db: Session = Depends(get_db)):
    """
    Create a new location
    """
    # Verify location type exists
    location_type = db.query(LocationType).filter(LocationType.id == location.location_type_id).first()
    if not location_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location type with ID {location.location_type_id} not found"
        )
    
    # Create new location
    new_location = Location(
        name=location.name,
        description=location.description,
        address=location.address,
        city=location.city,
        state=location.state,
        country=location.country,
        postal_code=location.postal_code,
        latitude=location.latitude,
        longitude=location.longitude,
        location_type_id=location.location_type_id
    )
    
    db.add(new_location)
    db.commit()
    db.refresh(new_location)
    
    return new_location

@router.get("/", response_model=List[LocationSchema])
def get_locations(
    skip: int = 0, 
    limit: int = 100, 
    location_type_id: int = None,
    db: Session = Depends(get_db)
):
    """
    Get all locations with optional filtering by location type
    """
    query = db.query(Location)
    
    if location_type_id:
        query = query.filter(Location.location_type_id == location_type_id)
    
    locations = query.offset(skip).limit(limit).all()
    return locations

@router.get("/{location_id}", response_model=LocationSchema)
def get_location(location_id: int, db: Session = Depends(get_db)):
    """
    Get location by ID
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {location_id} not found"
        )
    
    return location

@router.delete("/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(location_id: int, db: Session = Depends(get_db)):
    """
    Delete a location
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with ID {location_id} not found"
        )
    
    # Check if any devices are associated with this location
    if location.devices:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete location with ID {location_id} as it has associated devices"
        )
    
    db.delete(location)
    db.commit()
    
    return None