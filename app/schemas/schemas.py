from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id_users: int
    created: Optional[datetime] = None
    active: Optional[datetime] = None
    
    class Config:
        from_attributes = True

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
    description: Optional[str] = None
    identification: Optional[str] = None
    mac_address: Optional[str] = None
    id_users: int

class DeviceCreate(DeviceBase):
    pass

class DeviceUpdate(BaseModel):
    description: Optional[str] = None
    mac_address: Optional[str] = None

class Device(DeviceBase):
    id_device: int
    
    class Config:
        from_attributes = True

# Location schemas
class LocationBase(BaseModel):
    description: Optional[str] = None
    id_location_type: int
    id_device: int
    id_users_placed: int

class LocationCreate(LocationBase):
    pass

class Location(LocationBase):
    id_locations: int
    when_created: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# MQTT Entry schemas
class MQTTEntryBase(BaseModel):
    topic: str
    payload: str
    id_topics: int

class MQTTEntryCreate(MQTTEntryBase):
    pass

class MQTTEntry(MQTTEntryBase):
    id_mqttenteries: int
    time: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# MQTT Message schema for incoming messages
class MQTTMessage(BaseModel):
    topic: str
    payload: str
    qos: int = 0
    device_id: Optional[str] = None