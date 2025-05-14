"""
Modul pro definici API endpointů týkajících se uživatelů.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import users as user_service
from app.services import auth as auth_service
from app.schemas import schemas
from app.models import models

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

@router.get("/me", response_model=schemas.UserMeResponse, summary="Získání informací o přihlášeném uživateli", description="Vrátí detailní informace o aktuálně přihlášeném uživateli, včetně jeho jména, emailu, data vytvoření, poslední aktivity a seznamu přiřazených rolí.")
async def read_users_me(
    current_user: models.User = Depends(auth_service.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Endpoint pro získání informací o aktuálně přihlášeném uživateli.

    Vyžaduje autentizaci. Data jsou načtena pomocí `get_user_me_service`.

    Args:
        current_user (models.User): Objekt aktuálně přihlášeného uživatele,
                                     získaný z `get_current_active_user`.
        db (Session): Databázová session.

    Returns:
        schemas.UserMeResponse: Pydantic model s informacemi o uživateli.
    """
    # Volání servisní funkce pro získání dat uživatele
    # current_user.id je ID přihlášeného uživatele (UUID string)
    user_details = user_service.get_user_me_service(db, user_id=current_user.id)
    if not user_details:
        # Tento případ by neměl nastat, pokud get_user_me_service správně vyvolá výjimku
        # nebo pokud je uživatel vždy nalezen (což by měl být po úspěšné autentizaci).
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Přihlášený uživatel nebyl nalezen v databázi.",
        )
    return user_details