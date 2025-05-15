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
        "The view is refreshed on each request to provide the latest data."
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
        "The view is refreshed on each request to provide the latest data."
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
    
    try:
        # Check if mqttenteries table exists and has required columns
        check_table_query = """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'mqttenteries'
            );
        """
        if not db.execute(text(check_table_query)).scalar():
            logger.error("Required table 'mqttenteries' does not exist")
            raise HTTPException(status_code=500, detail="Required database table does not exist")
        
        # Get column information
        columns_query = "SELECT column_name FROM information_schema.columns WHERE table_name = 'mqttenteries';"
        columns = [row[0] for row in db.execute(text(columns_query)).fetchall()]
        
        if 'payload' not in columns:
            logger.error("Required 'payload' column not found")
            raise HTTPException(status_code=500, detail="Database schema incorrect")
        
        # Find time column if available
        time_column = next((col for col in columns 
                           if col.lower() in ['time', 'timestamp', 'created_at', 'updated_at']), None)
        
        # Build the query based on available columns
        query_parts = []
        
        # Select clause
        select_clause = "SELECT payload, topic"
        if time_column:
            select_clause += f", {time_column}"
        
        # From clause
        from_clause = "FROM mqttenteries"
        
        # Where clause
        where_conditions = []
        if raspberry_uuid and 'topic' in columns:
            where_conditions.append(f"topic LIKE '%{raspberry_uuid}%'")
        if time_column:
            where_conditions.append(f"{time_column} >= NOW() - INTERVAL '30 seconds'")
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Order by clause
        order_by = f"ORDER BY {time_column} DESC" if time_column else "ORDER BY id_mqttenteries DESC"
        
        # Limit clause - only needed if no time filtering
        limit_clause = "LIMIT 1000" if not time_column else ""
        
        # Build and execute final query
        final_query = f"{select_clause} {from_clause} {where_clause} {order_by} {limit_clause}"
        all_payloads = db.execute(text(final_query)).fetchall()
        logger.info(f"Found {len(all_payloads)} recent entries to analyze")
        
        # Use a dictionary to track MAC addresses per Raspberry
        raspberry_macs = {}
        
        # Calculate cutoff time for recent entries
        import datetime
        current_time = datetime.datetime.now()
        cutoff_time = current_time - datetime.timedelta(seconds=30)
        
        # Process payloads
        for row in all_payloads:
            try:
                import ast
                payload_dict = ast.literal_eval(row.payload)
                
                # Check if entry is recent based on timestamp if present
                is_recent = True
                if 'timestamp' in payload_dict:
                    try:
                        timestamp_str = payload_dict['timestamp'].replace('T', ' ')
                        timestamp_format = '%Y-%m-%d %H:%M:%S.%f' if '.' in timestamp_str else '%Y-%m-%d %H:%M:%S'
                        entry_time = datetime.datetime.strptime(timestamp_str, timestamp_format)
                        is_recent = entry_time >= cutoff_time
                        if not is_recent:
                            continue
                    except Exception as e:
                        logger.warning(f"Failed to parse timestamp: {e}")
                
                # Determine raspberry UUID
                rasp_id = None
                
                # Direct raspberry_uuid field
                if 'raspberry_uuid' in payload_dict:
                    rasp_id = payload_dict['raspberry_uuid']
                # Check in data.raspberry_uuid
                elif 'data' in payload_dict and isinstance(payload_dict['data'], dict) and 'raspberry_uuid' in payload_dict['data']:
                    rasp_id = payload_dict['data']['raspberry_uuid']
                # Try from topic
                elif hasattr(row, 'topic') and row.topic:
                    parts = row.topic.split('/')
                    if len(parts) >= 2:
                        rasp_id = parts[-2]
                
                # Filter by specific raspberry if provided
                if raspberry_uuid and rasp_id != raspberry_uuid:
                    continue
                
                if not rasp_id:
                    continue
                    
                # Initialize set for this raspberry if not exists
                if rasp_id not in raspberry_macs:
                    raspberry_macs[rasp_id] = set()
                    
                # Find MAC address in payload
                mac = None
                if 'data' in payload_dict and 'mac' in payload_dict['data']:
                    mac = payload_dict['data']['mac']
                elif 'mac' in payload_dict:
                    mac = payload_dict['mac']
                elif 'mac_address' in payload_dict:
                    mac = payload_dict['mac_address']
                
                if mac:
                    raspberry_macs[rasp_id].add(mac)
                    
            except Exception as e:
                logger.warning(f"Failed to parse payload: {e}")
                continue
        
        # If specific raspberry requested but not found, return zero
        if raspberry_uuid and raspberry_uuid not in raspberry_macs:
            logger.info(f"Raspberry UUID {raspberry_uuid} not found in recent data")
            return [RaspberryDeviceCount(raspberry_uuid=raspberry_uuid, device_count=0)]
        
        # Format results
        result = [
            RaspberryDeviceCount(
                raspberry_uuid=rasp_id,
                device_count=len(mac_addresses)
            )
            for rasp_id, mac_addresses in raspberry_macs.items()
        ]
        
        # If filtering for one raspberry, only return that one
        if raspberry_uuid:
            result = [r for r in result if r.raspberry_uuid == raspberry_uuid]
            
        logger.info(f"Returning {len(result)} raspberry UUIDs with device counts")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        endpoint = f"/devices_per_raspberry/{raspberry_uuid}" if raspberry_uuid else "/devices_per_raspberry"
        logger.error(f"Database query failed for {endpoint}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while querying device statistics")