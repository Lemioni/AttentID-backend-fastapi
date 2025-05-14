import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import models
from app.schemas import schemas

def create_device_service(db: Session, device: schemas.DeviceCreate, user_id: str):
    """
    Přidá nové zařízení do databáze s UUID identifikátorem.

    Args:
        db (Session): Databázová session.
        device (schemas.DeviceCreate): Data nového zařízení.
        user_id (str): ID uživatele, který vytváří zařízení (získáno z tokenu).

    Returns:
        models.Device: Vytvořené zařízení.

    Raises:
        HTTPException: Pokud zařízení s danou identifikací již existuje.
    """
    # Ověření uživatele není potřeba - uživatel je již ověřen přes token
    # a jeho ID je předáváno přímo jako parametr
    
    # Ověření, zda zařízení s danou identifikací již existuje
    existing_device = db.query(models.Device).filter(
        models.Device.identification == device.identification
    ).first()
    
    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Zařízení s touto identifikací již existuje."
        )    # Vytvoření nového zařízení - id_device se generuje automaticky v modelu
    # a id_user se nastavuje na ID přihlášeného uživatele
    db_device = models.Device(
        description=device.description,
        identification=device.identification,
        mac_address=device.mac_address,
        id_user=user_id  # Použití ID aktuálně přihlášeného uživatele
    )
    
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def get_devices(db: Session, skip: int = 0, limit: int = 100):
    """
    Získá seznam všech zařízení v databázi.

    Args:
        db (Session): Databázová session.
        skip (int): Počet záznamů k přeskočení.
        limit (int): Maximální počet záznamů.

    Returns:
        List[models.Device]: Seznam zařízení.
    """
    return db.query(models.Device).offset(skip).limit(limit).all()

def get_device(db: Session, device_id: str):
    """
    Získá zařízení podle ID.

    Args:
        db (Session): Databázová session.
        device_id (str): ID zařízení jako UUID řetězec.

    Returns:
        models.Device: Nalezené zařízení.

    Raises:
        HTTPException: Pokud zařízení s daným ID není nalezeno.
    """
    device = db.query(models.Device).filter(models.Device.id_device == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zařízení s tímto ID nebylo nalezeno."
        )
    return device
