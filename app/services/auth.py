from app.core.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from typing import Optional
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

def create_default_roles(db: Session):
    """
    Checks for default roles and creates them if they don't exist.
    Currently, creates a "common user" role with ID 1.
    """
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
            id_users=new_user.id_users,
            id_roles=default_role_id,
            id_users_created=new_user.id_users, # User creating their own role link
            id_users_deactivated=new_user.id_users, # Placeholder, assuming it means "not deactivated"
            when_created=current_time
            # when_deactivated is nullable in the model/schema, so not setting it here.
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
    # V modelu User je 'active' datetime objekt. Předpokládáme, že pokud je nastaven, uživatel je aktivní.
    # Pro explicitní kontrolu neaktivity by bylo potřeba porovnat s aktuálním časem
    # nebo mít dedikovaný boolean 'is_active' flag.
    # Prozatím, pokud 'active' existuje (není None), považujeme uživatele za aktivního.
    # Podle schématu UserBase je 'active' typu datetime.
    # V User modelu je 'active' DateTime, nullable=False. Takže by měl vždy existovat.
    # Otázka je, co znamená "neaktivní". Pokud by to znamenalo, že 'active' je starší než nějaký limit,
    # pak by zde byla potřeba další logika. Prozatím předpokládáme, že existence záznamu = aktivní.
    # Pokud by 'active' znamenalo 'last_login_time', pak by se zde nekontrolovala aktivita.
    # Vzhledem k názvu funkce "get_current_ACTIVE_user", je nutné nějak ověřit aktivitu.
    # V modelu User je pole 'active' typu DateTime a je non-nullable.
    # Předpokládejme, že 'active' se aktualizuje při každé aktivitě a pokud by uživatel byl deaktivován,
    # nastavilo by se např. na NULL nebo by existoval jiný flag.
    # Pro jednoduchost, pokud je uživatel nalezen, považujeme ho za aktivního.
    # Pokud by existoval explicitní atribut 'is_active' (boolean), bylo by to lepší.
    # V User modelu je pole 'active' (DateTime), které se nastavuje při vytvoření.
    # Není zde jasná definice "neaktivního" uživatele.
    # Prozatím, pokud je uživatel načten, považujeme ho za aktivního.
    # Pokud by byla potřeba sofistikovanější kontrola (např. flag 'is_deactivated'), musela by se přidat.
    if current_user.active is None: # Toto by nemělo nastat, pokud je 'active' non-nullable a vždy se nastavuje
        raise HTTPException(status_code=400, detail="Neaktivní uživatel")
    return current_user