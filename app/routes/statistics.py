import logging # Add logging import
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel

# Assuming Container is in app.core.container
# If not, the user needs to adjust this import
from app.core.container import container, get_db_session # Import the new dependency function

class RaspberryDeviceCount(BaseModel):
    raspberry_uuid: str
    device_count: int

router = APIRouter(
    prefix="/statistics",
    tags=["Statistics"],
)

@router.get(
    "/devices_per_raspberry",
    response_model=List[RaspberryDeviceCount],
    summary="Count of newest unique devices per Raspberry Pi UUID",
    description=(
        "Queries the `newest_device_enteries` materialized view to count the "
        "newest unique device entries (MAC addresses) for each Raspberry Pi UUID. "
        "Note: The materialized view (`newest_device_enteries`) should be refreshed "
        "periodically in your database for this endpoint to return up-to-date data."
    )
)
async def get_devices_per_raspberry(
    db: Session = Depends(get_db_session) # Use the new dependency function
):
    # Original implementation for all raspberry devices
    return await _get_devices_per_raspberry(None, db)

@router.get(
    "/devices_per_raspberry/{raspberry_uuid}",
    response_model=List[RaspberryDeviceCount],
    summary="Count of newest unique devices for a specific Raspberry Pi UUID",
    description=(
        "Queries the `newest_device_enteries` materialized view to count the "
        "newest unique device entries (MAC addresses) for a specific Raspberry Pi UUID. "
        "Note: The materialized view (`newest_device_enteries`) should be refreshed "
        "periodically in your database for this endpoint to return up-to-date data."
    )
)
async def get_devices_for_specific_raspberry(
    raspberry_uuid: str = Path(..., description="UUID of the Raspberry Pi to filter by"),
    db: Session = Depends(get_db_session)
):
    # Implementation for a specific raspberry device
    return await _get_devices_per_raspberry(raspberry_uuid, db)

async def _get_devices_per_raspberry(raspberry_uuid: Optional[str], db: Session):
    """Helper function to get device counts, optionally filtered by raspberry_uuid"""
    
    logger = logging.getLogger(__name__)
    
    # Check if the materialized view exists
    try:
        check_view_exists = """
            SELECT EXISTS (
                SELECT FROM pg_matviews 
                WHERE matviewname = 'newest_device_enteries'
            );
        """
        view_exists = db.execute(text(check_view_exists)).scalar()
        if not view_exists:
            logger.error("Materialized view 'newest_device_enteries' does not exist")
            raise HTTPException(
                status_code=500,
                detail="Required database view does not exist. Contact administrator."
            )
        
        # Add logging for debugging
        if raspberry_uuid:
            logger.info(f"Querying devices for specific Raspberry Pi: {raspberry_uuid}")
            
            # First check if this raspberry_uuid exists at all
            check_raspberry_exists = """
                SELECT EXISTS (
                    SELECT 1 FROM newest_device_enteries 
                    WHERE raspberry_uuid = :raspberry_uuid
                );
            """
            raspberry_exists = db.execute(
                text(check_raspberry_exists), 
                {"raspberry_uuid": raspberry_uuid}
            ).scalar()
            
            # If raspberry doesn't exist in our data, return zero count immediately
            if not raspberry_exists:
                logger.info(f"Raspberry UUID {raspberry_uuid} not found in data")
                return [RaspberryDeviceCount(raspberry_uuid=raspberry_uuid, device_count=0)]
            
            # If it exists, proceed with the count query
            query_str = """
                SELECT raspberry_uuid, COUNT(DISTINCT found_mac_address) AS device_count
                FROM newest_device_enteries
                WHERE raspberry_uuid = :raspberry_uuid
                GROUP BY raspberry_uuid;
            """
            result_proxy = db.execute(text(query_str), {"raspberry_uuid": raspberry_uuid})
        else:
            logger.info("Querying devices for all Raspberry Pis")
            query_str = """
                SELECT raspberry_uuid, COUNT(DISTINCT found_mac_address) AS device_count
                FROM newest_device_enteries
                GROUP BY raspberry_uuid
                ORDER BY raspberry_uuid;
            """
            result_proxy = db.execute(text(query_str))
            
        fetched_results = result_proxy.fetchall()
        
        # Handle empty result (should only happen if there's a problem, as we checked existence)
        if not fetched_results and raspberry_uuid:
            logger.warning(f"No device count results for Raspberry UUID {raspberry_uuid} despite existing in db")
            return [RaspberryDeviceCount(raspberry_uuid=raspberry_uuid, device_count=0)]
        
        # Convert results to Pydantic models
        result = [
            RaspberryDeviceCount(
                raspberry_uuid=str(row.raspberry_uuid), 
                device_count=int(row.device_count)
            )
            for row in fetched_results
        ]
        
        logger.info(f"Returning {len(result)} device count entries")
        return result
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        endpoint = f"/devices_per_raspberry/{raspberry_uuid}" if raspberry_uuid else "/devices_per_raspberry"
        logger.error(f"Database query failed for {endpoint}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while querying device statistics."
        )