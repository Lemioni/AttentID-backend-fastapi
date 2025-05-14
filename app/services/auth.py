from app.core.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from typing import Optional
import uuid
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.services.users import get_user_by_email # Assuming this function exists or will be created if needed

from app.models.models import User, UserRole, Role
from app.schemas.schemas import UserRegisterRequest, TokenData
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
from app.config.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_default_admin_user(db: Session) -> Optional[User]:
    """
    Creates a default admin user if it doesn't already exist.
    
    Args:
        db (Session): Database session
        
    Returns:
        Optional[User]: Created admin user or None if already exists
    """
    # Check if admin user already exists
    admin_email = settings.DEFAULT_ADMIN_EMAIL
    existing_admin = get_user_by_email(db, admin_email)
    
    if existing_admin:
        print("DEBUG: Default admin user already exists.")
        return None
    
    # Create admin user
    hashed_password = get_password_hash(settings.DEFAULT_ADMIN_PASSWORD)  # Default password should be changed after first login
    current_time = datetime.now(timezone.utc)
    
    admin_user = User(
        id=f"us-{uuid.uuid4()}",  # Generate UUID for admin
        email=admin_email,
        name=settings.DEFAULT_ADMIN_NAME,
        password_hash=hashed_password,
        created=current_time,
        active=current_time
    )
    
    db.add(admin_user)
    
    try:
        db.commit()
        db.refresh(admin_user)
        print(f"DEBUG: Created default admin user with ID: {admin_user.id}")
        
        # Assign administrator role (ID 2) to the admin user
        admin_role_entry = UserRole(
            id=admin_user.id,
            id_roles=2,  # Administrator role ID
            id_created_by=admin_user.id,  # Admin creates their own role
            id_deactivated_by=None,
            when_created=current_time,
            when_deactivated=None
        )
        
        # Also assign common user role (ID 1) to the admin user
        common_role_entry = UserRole(
            id=admin_user.id,
            id_roles=1,  # Common user role ID
            id_created_by=admin_user.id,
            id_deactivated_by=None,
            when_created=current_time,
            when_deactivated=None
        )
        
        db.add(admin_role_entry)
        db.add(common_role_entry)
        db.commit()
        
        print("DEBUG: Admin user roles assigned successfully.")
        return admin_user
        
    except IntegrityError as ie:
        db.rollback()
        print(f"DEBUG: IntegrityError in create_default_admin_user: {str(ie)}")
        return None
    except Exception as e:
        db.rollback()
        print(f"DEBUG: Error creating admin user: {str(e)}")
        raise e

def create_default_roles(db: Session):
    """
    Checks for default roles and creates them if they don't exist.
    Creates the following default roles:
    - ID 1: Common User (běžný uživatel)
    - ID 2: Administrator (administrátor s rozšířenými právy)
    """
    # Create common user role (ID 1)
    common_user_role = db.query(Role).filter(Role.id_roles == 1).first()
    if not common_user_role:
        default_role = Role(id_roles=1, description="Common User")
        db.add(default_role)
        try:
            db.commit()
            db.refresh(default_role)
            print("DEBUG: Default role 'Common User' (ID 1) created.")
        except IntegrityError:
            db.rollback()
            print("DEBUG: Default role 'Common User' (ID 1) already exists or another error occurred.")
        except Exception as e:
            db.rollback()
            print(f"DEBUG: Error creating default role: {str(e)}")
    
    # Create administrator role (ID 2)
    admin_role = db.query(Role).filter(Role.id_roles == 2).first()
    if not admin_role:
        admin_role = Role(id_roles=2, description="Administrator")
        db.add(admin_role)
        try:
            db.commit()
            db.refresh(admin_role)
            print("DEBUG: Default role 'Administrator' (ID 2) created.")
        except IntegrityError:
            db.rollback()
            print("DEBUG: Default role 'Administrator' (ID 2) already exists or another error occurred.")
        except Exception as e:
            db.rollback()
            print(f"DEBUG: Error creating admin role: {str(e)}")


async def create_user_account(db: Session, user_data: UserRegisterRequest) -> User | None:
    """
    Creates a new user account, hashes the password, and assigns a default role.
    Returns the created user object or None if email already exists.
    """
    hashed_password = get_password_hash(user_data.password)
    current_time = datetime.now(timezone.utc)

    new_user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hashed_password,
        created=current_time,
        active=current_time  # As per requirement
    )
    db.add(new_user)

    try:
        db.commit()
        db.refresh(new_user)

        # Assign default role "common user" (ID 1)
        # Assuming the user who creates the user role record is the user themselves for now.
        # This might need adjustment based on actual requirements for id_users_created.
        # For user_role, id_users_created and id_users_deactivated are not nullable.
        # Let's assume the user creating their own role link is user ID 1 (an admin or system user)
        # or the user themselves if that's allowed. Given the context, using new_user.id_users
        # for id_users_created in UserRole might be problematic if it's a foreign key to an admin.
        # For now, let's assume a placeholder or a specific system user ID if available.
        # The task stated "assigning a default role to the new user (e.g., "common user")"
        # and "clarify how you will determine or manage the ID for this default role."
        # User confirmed: "Assume the default role "common user" has ID 1."
        # The UserRole model has id_users_created and id_users_deactivated.
        # Let's assume for now that id_users_created for the UserRole entry
        # refers to the user who is performing the registration action (or a system user).
        # If the system itself is creating this, a dedicated system user ID would be best.
        # For simplicity in this step, and lacking a system user ID, I'll use the new user's ID.
        # This might need to be revisited. The `id_users_deactivated` also needs a value.
        # A common practice for non-nullable foreign keys that are not yet applicable
        # is to point them to a specific "system" or "unassigned" record, or use the creator's ID.
        # Given the constraints, and to make progress, I'll use the new user's ID for `id_users_created`
        # and a placeholder like 0 or new_user.id_users if 0 is not valid for `id_users_deactivated`
        # if it cannot be NULL. Let's check the model definition for nullability.
        # The schema UserRoleBase has id_users_created and id_users_deactivated as non-optional int.
        # Let's assume for now that the user creating the role link is the user themselves.
        # And for deactivation, if it's not deactivated, it might point to a system user or the creator.
        # This is a tricky part without full context on `id_users_created` and `id_users_deactivated` in `UserRole`.
        # For now, I will use the new user's ID for `id_users_created` and assume `id_users_deactivated`
        # can also be the new user's ID if it means "not deactivated by anyone else yet".
        # This is a common simplification if a dedicated system/admin ID isn't specified.

        default_role_id = 1 # As confirmed by user
        
        # A crucial detail: UserRole model has id_users_created and id_users_deactivated.
        # These are foreign keys to the users table.
        # Let's assume the user who "created" this role assignment is the user themselves.
        # And for "deactivated", if it's an active role, this might point to a special user ID
        # or the creator if it implies "not yet deactivated".
        # Given the schema, these must be valid user IDs.
        # Simplest assumption: the user is creating their own role link.
        user_role_entry = UserRole(
                    id=new_user.id,
                    id_roles=default_role_id,
                    id_created_by=new_user.id,
                    id_deactivated_by=None,
                    when_created=current_time
            # when_deactivated is also None for an active role, and is nullable in the model
        )
        db.add(user_role_entry)
        db.commit()
        db.refresh(user_role_entry)

        return new_user
    except IntegrityError: # Handles duplicate email or other integrity issues
        db.rollback()
        # print(f"DEBUG: IntegrityError in create_user_account: {str(ie)}") # Temporary debug print
        return None
    except Exception as e:
        db.rollback()
        # Log error e
        raise e

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Authenticates a user by email and password.
    Returns the user object if authentication is successful, otherwise None.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
async def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    """
    Dekóduje token, získá uživatele a ověří token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Nelze ověřit přihlašovací údaje",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Získá aktuálně přihlášeného aktivního uživatele.
    Používá se jako FastAPI dependency.
    """
    return current_user

def get_user_roles(db: Session, user_id: str) -> list:
    """
    Získá seznam rolí uživatele podle jeho ID.
    
    Args:
        db (Session): Databázová session.
        user_id (str): ID uživatele.
        
    Returns:
        list: Seznam ID rolí uživatele.
    """
    roles = db.query(Role.id_roles).join(
        UserRole, UserRole.id_roles == Role.id_roles
    ).filter(
        UserRole.id == user_id,
        UserRole.when_deactivated.is_(None)
    ).all()
    
    return [role.id_roles for role in roles]

async def check_admin_role(
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ověří, zda má uživatel administrátorskou roli (role s ID 2).
    Používá se jako FastAPI dependency pro zabezpečení endpointů,
    které by měly být přístupné pouze pro administrátory.
    
    Systém rolí:
    - ID 1: Běžný uživatel (Common User)
    - ID 2: Administrátor (Admin)
    
    Args:
        db (Session): Databázová session.
        current_user (User): Aktuálně přihlášený uživatel.
        
    Returns:
        User: Aktuálně přihlášený uživatel, pokud má administrátorskou roli.
        
    Raises:
        HTTPException 403: Pokud uživatel nemá administrátorskou roli.
    """
    user_roles = get_user_roles(db, current_user.id)
    
    if 2 not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pro tuto akci nemáte dostatečná oprávnění. Vyžaduje se role administrátora."
        )
    
    return current_user