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
        latitude=device.latitude,
        longitude=device.longitude,
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
    
def update_device_service(db: Session, device_id: str, device_data: schemas.DeviceUpdate):
    """
    Aktualizuje údaje zařízení podle ID.
    
    Args:
        db (Session): Databázová session.
        device_id (str): ID zařízení, které se má aktualizovat.
        device_data (schemas.DeviceUpdate): Nová data zařízení.
        
    Returns:
        models.Device: Aktualizované zařízení.
        
    Raises:
        HTTPException: Pokud zařízení s daným ID není nalezeno.
    """
    # Získání zařízení z databáze
    device = db.query(models.Device).filter(models.Device.id_device == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zařízení s tímto ID nebylo nalezeno."
        )
    
    # Aktualizace jednotlivých atributů
    if device_data.description is not None:
        device.description = device_data.description
    if device_data.mac_address is not None:
        device.mac_address = device_data.mac_address
    if device_data.latitude is not None:
        device.latitude = device_data.latitude
    if device_data.longitude is not None:
        device.longitude = device_data.longitude
    
    # Uložení změn
    db.commit()
    db.refresh(device)
    return device

def delete_device_service(db: Session, device_id: str):
    """
    Smaže zařízení podle ID.
    
    Args:
        db (Session): Databázová session.
        device_id (str): ID zařízení, které má být smazáno.
        
    Returns:
        bool: True pokud bylo zařízení úspěšně smazáno.
        
    Raises:
        HTTPException: Pokud zařízení s daným ID není nalezeno.
    """
    # Získání zařízení z databáze
    device = db.query(models.Device).filter(models.Device.id_device == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zařízení s tímto ID nebylo nalezeno."
        )
    
    # Kontrola, zda zařízení nemá navázané lokace
    if device.locations and len(device.locations) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Zařízení nemůže být smazáno, protože má přiřazené lokace. Nejprve odstraňte lokace."
        )
    
    # Smazání zařízení
    db.delete(device)
    db.commit()
    return True
