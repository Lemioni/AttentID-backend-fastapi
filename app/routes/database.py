from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.services.database import DatabaseService

router = APIRouter(prefix="/database", tags=["Database"])

@router.post("/populate-all", status_code=202)
async def populate_all_test_data(
    background_tasks: BackgroundTasks,
    db_service: DatabaseService = Depends()
):
    """
    Populate all database tables with test data in the correct order
    """
    background_tasks.add_task(db_service.populate_test_data)
    
    return {
        "message": "Database population started in the background",
        "note": "Check individual population endpoints for detailed results"
    }

@router.get("/status", response_model=Dict[str, Any])
def get_database_status(
    db_service: DatabaseService = Depends()
):
    """
    Get counts of records in all tables to check database status
    """
    return db_service.get_database_status() 