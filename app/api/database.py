from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import requests

from app.core.database import get_db

router = APIRouter()

@router.post("/populate-all", status_code=status.HTTP_202_ACCEPTED)
async def populate_all_test_data(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Populate all database tables with test data in the correct order to satisfy foreign key constraints
    """
    # Define the API endpoint URLs in the correct dependency order
    endpoints = [
        "/users/populate-test-data",       # First users (no dependencies)
        "/roles/populate-test-data",       # Then roles (no dependencies)
        "/user-roles/populate-test-data",  # Then user-roles (depends on users and roles)
        "/topics/populate-test-data",      # Then topics (depends on users)
        "/location-types/populate-test-data", # Then location types (depends on topics)
        "/devices/populate-test-data",     # Then devices (depends on users)
        "/mqtt-entries/populate-test-data" # Then MQTT entries (depends on topics)
    ]

    # Function to call the endpoints in the background
    def populate_in_background():
        base_url = "http://localhost:8000"  # Adjust if your app runs on a different port
        results = {}
        
        for endpoint in endpoints:
            try:
                response = requests.post(f"{base_url}{endpoint}")
                results[endpoint] = {
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 201 else None
                }
            except Exception as e:
                results[endpoint] = {
                    "error": str(e)
                }
        
        return results

    # Add the population task to the background tasks
    background_tasks.add_task(populate_in_background)
    
    return {
        "message": "Database population started in the background",
        "note": "Check individual population endpoints for detailed results"
    }

@router.get("/status", response_model=Dict[str, Any])
def get_database_status(db: Session = Depends(get_db)):
    """
    Get counts of records in all tables to check database status
    """
    # Define SQL queries to count records in each table
    table_queries = {
        "users": "SELECT COUNT(*) FROM users",
        "roles": "SELECT COUNT(*) FROM roles",
        "user_roles": "SELECT COUNT(*) FROM user_role",
        "topics": "SELECT COUNT(*) FROM topics",
        "location_types": "SELECT COUNT(*) FROM location_type",
        "devices": "SELECT COUNT(*) FROM device",
        "locations": "SELECT COUNT(*) FROM locations",
        "mqtt_entries": "SELECT COUNT(*) FROM mqttenteries"
    }
    
    results = {}
    
    # Execute each query and store the result
    for table_name, query in table_queries.items():
        result = db.execute(query).scalar()
        results[table_name] = result
    
    return {
        "database_status": "ok",
        "record_counts": results
    }
