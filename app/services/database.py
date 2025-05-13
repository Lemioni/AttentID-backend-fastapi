from typing import Dict, Any
from sqlalchemy.orm import Session
from fastapi import Depends
import requests

from app.core.database import get_db
from app.config.settings import settings

class DatabaseService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
    
    async def populate_test_data(self) -> Dict[str, Any]:
        """Populate all database tables with test data"""
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

        base_url = f"http://localhost:8000{settings.API_V1_STR}"
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
    
    def get_database_status(self) -> Dict[str, Any]:
        """Get counts of records in all tables"""
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
        
        results = {
            table_name: self.db.execute(query).scalar()
            for table_name, query in table_queries.items()
        }
        
        return {
            "database_status": "ok",
            "record_counts": results
        } 