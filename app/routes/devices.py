"""
Modul obsahující endpointy pro správu zařízení.
Definuje rozhraní API pro manipulaci se zařízeními.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.services import devices
from app.schemas import schemas
from app.services.auth import get_current_user, check_admin_role
from app.models import models

router = APIRouter(prefix="/devices", tags=["Devices"])

@router.post("/", response_model=schemas.Device, status_code=status.HTTP_201_CREATED)
def create_device(
    device: schemas.DeviceCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(check_admin_role)
):
    """
    Vytvoří nové zařízení v databázi.
    
    Přidá do systému nové zařízení s následujícími parametry:
    - Identifikace zařízení (povinné)
    - Popis zařízení (volitelný)
    - MAC adresa zařízení (volitelná)
    
    ID zařízení (id_device) je generováno automaticky jako UUID 
    a není potřeba ho zadávat.
    
    ID uživatele, který zařízení přidává, je nastaveno automaticky 
    podle aktuálně přihlášeného uživatele.
    
    Před vytvořením zařízení se kontroluje:
    - zda má přihlášený uživatel administrátorská práva (role ID 2)
    - zda zařízení s danou identifikací již není v systému registrováno
    
    Args:
        device: Data nového zařízení.
        db: Databázová session.
        current_user: Aktuálně přihlášený uživatel s administrátorskými právy.
        
    Returns:
        Nově vytvořené zařízení s přiřazeným ID.
        
    Raises:
        HTTPException 403: Pokud uživatel nemá administrátorská práva.
        HTTPException 409: Pokud zařízení s danou identifikací již existuje.
    """
    # Předání ID aktuálního uživatele do service funkce
    return devices.create_device_service(db=db, device=device, user_id=current_user.id)

@router.get("/", response_model=List[schemas.Device])
def read_devices(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(check_admin_role)
):
    """
    Získá seznam zařízení. Vyžaduje administrátorská práva (role ID 2).
    
    Args:
        skip: Počet záznamů k přeskočení.
        limit: Maximální počet záznamů k vrácení.
        db: Databázová session.
        current_user: Aktuálně přihlášený uživatel s administrátorskými právy.
        
    Returns:
        Seznam zařízení.
        
    Raises:
        HTTPException 403: Pokud uživatel nemá administrátorská práva.
    """
    # Získání seznamu zařízení z databáze pomocí service funkce
    return devices.get_devices(db=db, skip=skip, limit=limit)

@router.get("/{device_id}", response_model=schemas.Device)
def read_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(check_admin_role)
):
    """
    Získá detail konkrétního zařízení podle ID. Vyžaduje administrátorská práva (role ID 2).
    
    Args:
        device_id: ID zařízení (UUID řetězec).
        db: Databázová session.
        current_user: Aktuálně přihlášený uživatel s administrátorskými právy.
        
    Returns:
        Detail zařízení.
        
    Raises:
        HTTPException 403: Pokud uživatel nemá administrátorská práva.
        HTTPException 404: Pokud zařízení s daným ID neexistuje.
    """
    return devices.get_device(db=db, device_id=device_id)
