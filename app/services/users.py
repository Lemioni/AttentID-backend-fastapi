"""
Modul pro servisní logiku týkající se uživatelů.
Obsahuje funkce pro získávání a manipulaci s daty uživatelů.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import models
from app.schemas import schemas

def get_user_me_service(db: Session, user_id: int) -> schemas.UserMeResponse:
    """
    Získá detailní informace o přihlášeném uživateli včetně jeho rolí.

    Args:
        db (Session): Databázová session.
        user_id (int): ID přihlášeného uživatele.

    Returns:
        schemas.UserMeResponse: Objekt s daty uživatele a jeho rolemi.

    Raises:
        HTTPException: Pokud uživatel s daným ID není nalezen.
    """
    # Načtení uživatele z databáze
    # Query for the user and their roles using joins
    user_db = db.query(
        models.User.id_users,
        models.User.name,
        models.User.email,
        models.User.created,
        models.User.active
    ).filter(models.User.id_users == user_id).first()

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
    .filter(models.UserRole.id_users == user_id)\
    .filter(models.UserRole.when_deactivated.is_(None)).all() # Zajistíme, že role jsou aktivní

    # Příprava seznamu rolí pro odpověď
    roles_list = [
        schemas.UserRoleDetail(id_roles=role.id_roles, description=role.description)
        for role in user_roles_db
    ]

    # Sestavení odpovědi
    user_response = schemas.UserMeResponse(
        id_users=user_db.id_users,
        name=user_db.name,
        email=user_db.email,
        created=user_db.created,
        last_active=user_db.active, # Mapování 'active' z DB na 'last_active' v schématu
        roles=roles_list
    )

    return user_response
def get_user_by_email(db: Session, email: str) -> models.User | None:
    """
    Získá uživatele podle emailové adresy.

    Args:
        db (Session): Databázová session.
        email (str): Emailová adresa uživatele.

    Returns:
        models.User | None: Objekt uživatele nebo None, pokud nebyl nalezen.
    """
    return db.query(models.User).filter(models.User.email == email).first()