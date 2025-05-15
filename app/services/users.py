"""
Modul pro servisní logiku týkající se uživatelů.
Obsahuje funkce pro získávání a manipulaci s daty uživatelů.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import models
from app.schemas import schemas
from app.core.password_utils import get_password_hash
# Import get_user_by_email from auth.py - toto vytvoří explicitní závislost
# ale cirkulární import je vyřešen přesunutím funkcí hashování do password_utils.py
from app.services.auth import get_user_by_email

def get_user_me_service(db: Session, user_id: str) -> schemas.UserMeResponse:  # Changed user_id type to str
    """
    Získá detailní informace o přihlášeném uživateli včetně jeho rolí.

    Args:
        db (Session): Databázová session.
        user_id (str): ID přihlášeného uživatele. # Changed user_id type to str

    Returns:
        schemas.UserMeResponse: Objekt s daty uživatele a jeho rolemi.

    Raises:
        HTTPException: Pokud uživatel s daným ID není nalezen.
    """
    # Načtení uživatele z databáze
    # Query for the user and their roles using joins
    user_db = db.query(
        models.User.id,  # Changed id_users to id
        models.User.name,
        models.User.email,
        models.User.created,
        models.User.active
    ).filter(models.User.id == user_id).first() # Changed id_users to id

    if not user_db:
        # Tento případ by neměl nastat, pokud je uživatel autentizován
        # a jeho ID je správně předáno z tokenu.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uživatel nebyl nalezen."
        )

    # Načtení rolí uživatele
    user_roles_db = db.query(
        models.Role.id_roles,
        models.Role.description
    ).join(models.UserRole, models.UserRole.id_roles == models.Role.id_roles)\
    .filter(models.UserRole.id == user_id)\
    .filter(models.UserRole.when_deactivated.is_(None)).all() # Zajistíme, že role jsou aktivní

    # Příprava seznamu rolí pro odpověď
    roles_list = [
        schemas.UserRoleDetail(id_roles=role.id_roles, description=role.description)
        for role in user_roles_db
    ]

    # Sestavení odpovědi
    user_response = schemas.UserMeResponse(
        id=user_db.id,  # Changed id_users to id
        name=user_db.name,
        email=user_db.email,
        created=user_db.created,
        last_active=user_db.active, # Mapování 'active' z DB na 'last_active' v schématu
        roles=roles_list
    )

    return user_response

# Funkce get_user_by_email je importována z auth.py

def get_user_by_id(db: Session, user_id: str) -> models.User | None:
    """
    Získá uživatele podle ID.

    Args:
        db (Session): Databázová session.
        user_id (str): ID uživatele.

    Returns:
        models.User | None: Objekt uživatele nebo None, pokud nebyl nalezen.
    """
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[schemas.UserListResponse]:
    """
    Získá seznam všech uživatelů.

    Args:
        db (Session): Databázová session.
        skip (int, optional): Počet přeskočených záznamů. Výchozí je 0.
        limit (int, optional): Maximální počet vrácených záznamů. Výchozí je 100.

    Returns:
        List[schemas.UserListResponse]: Seznam uživatelů.
    """
    users = db.query(models.User).offset(skip).limit(limit).all()
    
    # Convert to UserListResponse and ensure name is not None
    return [
        schemas.UserListResponse(
            id=user.id,
            email=user.email,
            name=user.name or "",  # Use empty string if name is None
            created=user.created,
            active=user.active
        )
        for user in users
    ]

def create_user(db: Session, user_data: schemas.UserCreateAdmin, admin_user_id: str) -> models.User:
    """
    Vytvoří nového uživatele.

    Args:
        db (Session): Databázová session.
        user_data (schemas.UserCreateAdmin): Data nového uživatele.
        admin_user_id (str): ID administrátora, který uživatele vytváří.

    Returns:
        models.User: Vytvořený uživatel.

    Raises:
        HTTPException: Pokud uživatel s daným emailem již existuje.
    """
    # Kontrola, zda email je již používán
    db_user = get_user_by_email(db, user_data.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email již existuje v systému")
        
    hashed_password = get_password_hash(user_data.password)
    current_time = datetime.now()
    
    db_user = models.User(
        id=f"us-{user_data.id}" if user_data.id else None,  # Použití ID, pokud je poskytnuto, jinak se vygeneruje automaticky
        email=user_data.email,
        name=user_data.name,
        password_hash=hashed_password,
        created=current_time,
        active=current_time
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Přidání rolí uživateli
    for role_id in user_data.roles:
        user_role = models.UserRole(
            id=db_user.id,
            id_roles=role_id,
            id_created_by=admin_user_id,
            when_created=current_time,
            id_deactivated_by=None,
            when_deactivated=None
        )
        db.add(user_role)
        
    db.commit()
    return db_user

def update_user(db: Session, user_id: str, user_data: schemas.UserUpdateAdmin, admin_user_id: str) -> Optional[models.User]:
    """
    Aktualizuje údaje uživatele.

    Args:
        db (Session): Databázová session.
        user_id (str): ID uživatele, který má být aktualizován.
        user_data (schemas.UserUpdateAdmin): Nová data uživatele.
        admin_user_id (str): ID administrátora, který provádí aktualizaci.

    Returns:
        Optional[models.User]: Aktualizovaný uživatel nebo None, pokud uživatel nebyl nalezen.

    Raises:
        HTTPException: Pokud je zadaný nový email, který již používá jiný uživatel.
    """
    db_user = get_user_by_id(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail=f"Uživatel s ID {user_id} nebyl nalezen")
        
    # Kontrola unikátnosti emailu, pokud je poskytnut nový
    if user_data.email and user_data.email != db_user.email:
        existing_user = get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(status_code=400, detail="Email již existuje v systému")
    
    # Aktualizace základních údajů
    update_data = {k: v for k, v in user_data.dict().items() if v is not None}
    
    # Zpracování hesla zvlášť
    if "password" in update_data:
        update_data["password_hash"] = get_password_hash(update_data.pop("password"))
    
    # Zpracování rolí zvlášť
    roles = None
    if "roles" in update_data:
        roles = update_data.pop("roles")
    
    # Aktualizace zbylých údajů
    for key, value in update_data.items():
        if hasattr(db_user, key):
            setattr(db_user, key, value)
    
    db.commit()
    
    # Aktualizace rolí, pokud jsou poskytnuty
    if roles:
        # Deaktivace stávajících rolí
        current_time = datetime.now()
        existing_roles = db.query(models.UserRole).filter(
            models.UserRole.id == user_id,
            models.UserRole.when_deactivated.is_(None)
        ).all()
        
        for role in existing_roles:
            role.when_deactivated = current_time
            role.id_deactivated_by = admin_user_id
        
        # Přidání nových rolí
        for role_id in roles:
            user_role = models.UserRole(
                id=user_id,
                id_roles=role_id,
                id_created_by=admin_user_id,
                when_created=current_time,
                id_deactivated_by=None,
                when_deactivated=None
            )
            db.add(user_role)
        
        db.commit()
    
    return db_user

def delete_user(db: Session, user_id: str) -> bool:
    """
    Smaže uživatele z databáze.

    Args:
        db (Session): Databázová session.
        user_id (str): ID uživatele, který má být smazán.

    Returns:
        bool: True pokud byl uživatel úspěšně smazán, jinak False.
        
    Raises:
        HTTPException: Pokud uživatel nebyl nalezen.
    """
    db_user = get_user_by_id(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail=f"Uživatel s ID {user_id} nebyl nalezen")
    
    # Nejprve smažeme všechny role uživatele
    db.query(models.UserRole).filter(models.UserRole.id == user_id).delete()
    
    # Poté smažeme samotného uživatele
    db.delete(db_user)
    db.commit()
    
    return True