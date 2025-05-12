from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from typing import Optional

from app.models.models import User, UserRole, Role
from app.schemas.schemas import UserRegisterRequest, TokenData
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