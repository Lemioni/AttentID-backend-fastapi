from sqlalchemy import Column, BigInteger, String, ForeignKey, DateTime, Text, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id_users = Column(BigInteger, primary_key=True)
    email = Column(Text)
    created = Column(DateTime)
    active = Column(DateTime)
    
    # Relationships
    devices = relationship("Device", back_populates="user")
    created_topics = relationship("Topic", back_populates="created_by")
    placed_locations = relationship("Location", back_populates="placed_by")
    user_roles = relationship("UserRole", foreign_keys="UserRole.id_users", back_populates="user")
    created_roles = relationship("UserRole", foreign_keys="UserRole.id_users_created", back_populates="created_by")
    deactivated_roles = relationship("UserRole", foreign_keys="UserRole.id_users_deactivated", back_populates="deactivated_by")

class Role(Base):
    __tablename__ = "roles"
    
    id_roles = Column(BigInteger, primary_key=True)
    description = Column(Text)
    
    # Relationships
    user_roles = relationship("UserRole", back_populates="role")

class UserRole(Base):
    __tablename__ = "user_role"
    
    id_user_role = Column(BigInteger, primary_key=True)
    id_users = Column(BigInteger, ForeignKey("users.id_users"))
    id_roles = Column(BigInteger, ForeignKey("roles.id_roles"))
    id_users_created = Column(BigInteger, ForeignKey("users.id_users"))
    when_created = Column(DateTime)
    id_users_deactivated = Column(BigInteger, ForeignKey("users.id_users"))
    when_deactivated = Column(DateTime)
    
    # Relationships
    user = relationship("User", foreign_keys=[id_users], back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")
    created_by = relationship("User", foreign_keys=[id_users_created], back_populates="created_roles")
    deactivated_by = relationship("User", foreign_keys=[id_users_deactivated], back_populates="deactivated_roles")

class Topic(Base):
    __tablename__ = "topics"
    
    id_topics = Column(BigInteger, primary_key=True)
    topic = Column(Text)
    id_users_created = Column(BigInteger, ForeignKey("users.id_users"))
    when_created = Column(DateTime)
    
    # Relationships
    created_by = relationship("User", back_populates="created_topics")
    mqtt_entries = relationship("MQTTEntry", back_populates="topic_rel")
    location_types = relationship("LocationType", back_populates="topic_rel")

class LocationType(Base):
    __tablename__ = "location_type"
    
    id_location_type = Column(BigInteger, primary_key=True)
    description = Column(Text)
    topic = Column(Text)
    id_topics = Column(BigInteger, ForeignKey("topics.id_topics"))
    
    # Relationships
    topic_rel = relationship("Topic", back_populates="location_types")
    locations = relationship("Location", back_populates="location_type")

class Device(Base):
    __tablename__ = "device"
    
    id_device = Column(BigInteger, primary_key=True)
    description = Column(Text)
    identification = Column(Text)
    mac_address = Column(Text)
    id_users = Column(BigInteger, ForeignKey("users.id_users"))
    
    # Relationships
    user = relationship("User", back_populates="devices")
    locations = relationship("Location", back_populates="device")

class Location(Base):
    __tablename__ = "locations"
    
    id_locations = Column(BigInteger, primary_key=True)
    description = Column(Text)
    id_location_type = Column(BigInteger, ForeignKey("location_type.id_location_type"))
    id_device = Column(BigInteger, ForeignKey("device.id_device"))
    id_users_placed = Column(BigInteger, ForeignKey("users.id_users"))
    when_created = Column(DateTime)
    
    # Relationships
    location_type = relationship("LocationType", back_populates="locations")
    device = relationship("Device", back_populates="locations")
    placed_by = relationship("User", back_populates="placed_locations")

class MQTTEntry(Base):
    __tablename__ = "mqttenteries"
    
    id_mqttenteries = Column(BigInteger, primary_key=True)
    time = Column(DateTime)
    topic = Column(Text)
    payload = Column(Text)
    id_topics = Column(BigInteger, ForeignKey("topics.id_topics"))
    
    # Relationships
    topic_rel = relationship("Topic", back_populates="mqtt_entries")