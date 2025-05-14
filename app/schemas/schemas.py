"""
Modul definující Pydantic schémata pro validaci dat.
Obsahuje modely pro validaci vstupních a výstupních dat API.
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

# User schemas
class UserBase(BaseModel):
    email: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id_users: str
    created: Optional[datetime] = None
    active: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Auth schemas
class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserRegisterResponseUser(BaseModel):
    id_users: str
    email: EmailStr
    name: str
    created: datetime

    class Config:
        from_attributes = True

class UserRegisterResponse(BaseModel):
    message: str
    user: UserRegisterResponseUser
# Schéma pro detail role v odpovědi /me
class UserRoleDetail(BaseModel):
    """
    Detail role uživatele pro UserMeResponse.
    Specifikuje id_roles a popis role.
    """
    id_roles: int
    description: str  # Popis role, např. "administrátor", "uživatel"

    class Config:
        from_attributes = True


# Schéma pro odpověď endpointu /api/users/me
class UserMeResponse(BaseModel):
    """
    Schéma pro odpověď endpointu /api/users/me.
    Obsahuje detailní informace o přihlášeném uživateli včetně jeho rolí.
    """
    id: str  # ID uživatele
    name: str  # Jméno uživatele
    email: EmailStr  # Emailová adresa uživatele
    created: datetime  # Datum a čas vytvoření účtu uživatele
    last_active: datetime  # Datum a čas poslední aktivity uživatele (z pole users.active)
    roles: List[UserRoleDetail]  # Seznam rolí přiřazených uživateli

    class Config:
        from_attributes = True # Umožňuje mapování z ORM modelu atributů na pole schématu
class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
# Role schemas
class RoleBase(BaseModel):
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class Role(RoleBase):
    id_roles: int
    
    class Config:
        from_attributes = True

# UserRole schemas
class UserRoleBase(BaseModel):
    id_users: int
    id_roles: int
    id_users_created: int
    id_users_deactivated: int

class UserRoleCreate(UserRoleBase):
    pass

class UserRole(UserRoleBase):
    id_user_role: int
    when_created: Optional[datetime] = None
    when_deactivated: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Topic schemas
class TopicBase(BaseModel):
    topic: Optional[str] = None
    id_users_created: int

class TopicCreate(TopicBase):
    pass

class Topic(TopicBase):
    id_topics: int
    when_created: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# LocationType schemas
class LocationTypeBase(BaseModel):
    description: Optional[str] = None
    topic: Optional[str] = None
    id_topics: int

class LocationTypeCreate(LocationTypeBase):
    pass

class LocationType(LocationTypeBase):
    id_location_type: int
    
    class Config:
        from_attributes = True

# Device schemas
class DeviceBase(BaseModel):
    """
    Základní schéma pro zařízení.
    Definuje společné atributy pro všechny operace se zařízeními.
    """
    description: Optional[str] = None
    identification: str  # Identifikace zařízení (např. UUID nebo jiný identifikátor)
    mac_address: Optional[str] = None

class DeviceCreate(BaseModel):
    """
    Schéma pro vytvoření nového zařízení.
    Obsahuje všechny potřebné údaje pro vytvoření zařízení.
    ID zařízení se generuje automaticky.
    ID uživatele, který zařízení přidává, je nastaveno automaticky 
    podle přihlášeného uživatele.
    """
    description: Optional[str] = None
    identification: str
    mac_address: Optional[str] = None
    
    @validator('mac_address')
    def validate_mac_address(cls, v):
        """Validace MAC adresy ve formátu XX:XX:XX:XX:XX:XX nebo XX-XX-XX-XX-XX-XX."""
        if v is None:
            return v
        # Validace formátu MAC adresy (XX:XX:XX:XX:XX:XX nebo XX-XX-XX-XX-XX-XX)
        pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
        if not re.match(pattern, v):
            raise ValueError('MAC adresa musí být ve formátu XX:XX:XX:XX:XX:XX nebo XX-XX-XX-XX-XX-XX')
        return v

class DeviceUpdate(BaseModel):
    """
    Schéma pro aktualizaci zařízení.
    Umožňuje aktualizovat pouze vybrané atributy.
    """
    description: Optional[str] = None
    mac_address: Optional[str] = None

class Device(BaseModel):
    """
    Schéma pro odpověď s daty zařízení.
    Obsahuje všechny atributy včetně automaticky vygenerovaného ID.
    """
    id_device: str
    description: Optional[str] = None
    identification: str
    mac_address: Optional[str] = None
    id_user: str  # ID uživatele, který zařízení přidal
    
    class Config:
        from_attributes = True

# Location schemas
class LocationBase(BaseModel):
    description: Optional[str] = None
    id_location_type: str
    id_device: str
    id_users_placed: str

class LocationCreate(LocationBase):
    pass

class Location(LocationBase):
    id_locations: str
    when_created: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Základní schémata pro MQTT záznamy
class MQTTEntryBase(BaseModel):
    """
    Základní schéma pro MQTT záznam.
    Definuje povinné atributy pro každý MQTT záznam.
    """
    topic: str  # Téma zprávy
    payload: str  # Obsah zprávy
    id_topics: int  # ID tématu v databázi

class MQTTEntryCreate(MQTTEntryBase):
    pass

class MQTTEntry(MQTTEntryBase):
    """
    Rozšířené schéma pro MQTT záznam.
    Přidává systémem generované atributy.
    """
    id_mqttenteries: int  # Unikátní ID záznamu
    time: Optional[datetime] = None  # Čas přijetí zprávy
    
    class Config:
        """Konfigurace pro Pydantic model."""
        from_attributes = True

# Schéma pro příchozí MQTT zprávy
class MQTTMessage(BaseModel):
    """
    Schéma pro příchozí MQTT zprávy.
    Používá se pro validaci zpráv přijatých přes MQTT.
    """
    topic: str  # Téma zprávy
    payload: str  # Obsah zprávy
    qos: int = 0  # Quality of Service úroveň
    device_id: Optional[str] = None  # Volitelný identifikátor zařízení