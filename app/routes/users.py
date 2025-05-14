"""
Modul pro definici API endpointů týkajících se uživatelů.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
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

# CRUD operace pro administrátory
@router.get("", response_model=List[schemas.UserListResponse], 
           summary="Seznam uživatelů",
           description="Vrátí seznam všech uživatelů. Vyžaduje administrátorská práva.")
async def get_users(
    skip: int = Query(0, description="Počet přeskočených záznamů"),
    limit: int = Query(100, description="Maximální počet vrácených záznamů"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_service.check_admin_role)
):
    """
    Získá seznam všech uživatelů.
    Tento endpoint je přístupný pouze pro administrátory.

    Args:
        skip (int): Počet přeskočených záznamů (pro stránkování).
        limit (int): Maximální počet vrácených záznamů (pro stránkování).
        db (Session): Databázová session.
        current_user (models.User): Přihlášený uživatel s administrátorskými právy.

    Returns:
        List[schemas.UserListResponse]: Seznam uživatelů.
    """
    users = user_service.get_all_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=schemas.UserMeResponse, 
           summary="Detail uživatele",
           description="Vrátí detailní informace o uživateli s daným ID. Vyžaduje administrátorská práva.")
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_service.check_admin_role)
):
    """
    Získá detailní informace o uživateli podle ID.
    Tento endpoint je přístupný pouze pro administrátory.

    Args:
        user_id (str): ID uživatele.
        db (Session): Databázová session.
        current_user (models.User): Přihlášený uživatel s administrátorskými právy.

    Returns:
        schemas.UserMeResponse: Detailní informace o uživateli.

    Raises:
        HTTPException: Pokud uživatel s daným ID neexistuje.
    """
    user_details = user_service.get_user_me_service(db, user_id=user_id)
    if not user_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Uživatel s ID {user_id} nebyl nalezen."
        )
    return user_details

@router.post("", response_model=schemas.User, status_code=status.HTTP_201_CREATED,
            summary="Vytvoření uživatele",
            description="Vytvoří nového uživatele. Vyžaduje administrátorská práva.")
async def create_user(
    user_data: schemas.UserCreateAdmin,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_service.check_admin_role)
):
    """
    Vytvoří nového uživatele.
    Tento endpoint je přístupný pouze pro administrátory.

    Args:
        user_data (schemas.UserCreateAdmin): Data nového uživatele.
        db (Session): Databázová session.
        current_user (models.User): Přihlášený uživatel s administrátorskými právy.

    Returns:
        schemas.User: Vytvořený uživatel.

    Raises:
        HTTPException: Pokud uživatel s daným emailem již existuje.
    """
    return user_service.create_user(db, user_data, admin_user_id=current_user.id)

@router.put("/{user_id}", response_model=schemas.User,
           summary="Aktualizace uživatele",
           description="Aktualizuje informace o uživateli s daným ID. Vyžaduje administrátorská práva.")
async def update_user(
    user_id: str,
    user_data: schemas.UserUpdateAdmin,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_service.check_admin_role)
):
    """
    Aktualizuje informace o uživateli.
    Tento endpoint je přístupný pouze pro administrátory.

    Args:
        user_id (str): ID uživatele, který má být aktualizován.
        user_data (schemas.UserUpdateAdmin): Nová data uživatele.
        db (Session): Databázová session.
        current_user (models.User): Přihlášený uživatel s administrátorskými právy.

    Returns:
        schemas.User: Aktualizovaný uživatel.

    Raises:
        HTTPException: Pokud uživatel s daným ID neexistuje nebo pokud nový email již používá jiný uživatel.
    """
    updated_user = user_service.update_user(db, user_id, user_data, admin_user_id=current_user.id)
    return updated_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
              summary="Smazání uživatele",
              description="Smaže uživatele s daným ID. Vyžaduje administrátorská práva.")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_service.check_admin_role)
):
    """
    Smaže uživatele.
    Tento endpoint je přístupný pouze pro administrátory.

    Args:
        user_id (str): ID uživatele, který má být smazán.
        db (Session): Databázová session.
        current_user (models.User): Přihlášený uživatel s administrátorskými právy.

    Returns:
        None

    Raises:
        HTTPException: Pokud uživatel s daným ID neexistuje.
    """
    # Ověření, že uživatel se nepokouší smazat sám sebe
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nemůžete smazat svůj vlastní účet."
        )
    
    user_service.delete_user(db, user_id)
    return None