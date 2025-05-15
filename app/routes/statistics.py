import logging # Add logging import
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
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
    query_str = """
        SELECT
            raspberry_uuid,
            COUNT(DISTINCT found_mac_address) AS device_count
        FROM
            newest_device_enteries
        GROUP BY
            raspberry_uuid
        ORDER BY
            raspberry_uuid;
    """
    try:
        result_proxy = db.execute(text(query_str))
        fetched_results = result_proxy.fetchall()
    except Exception as e:
        # It's good practice to log the actual error
        logger = logging.getLogger(__name__)
        logger.error(f"Database query failed for /devices_per_raspberry: {e}", exc_info=True) # Uncommented
        raise HTTPException(
            status_code=500,
            detail="An error occurred while querying device statistics."
        )

    response_data = [
        RaspberryDeviceCount(raspberry_uuid=str(row.raspberry_uuid), device_count=int(row.device_count))
        for row in fetched_results
    ]
    return response_data
