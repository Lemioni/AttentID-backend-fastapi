"""
Modul pro práci s hesly.
Obsahuje funkce pro hashování a ověření hesel.
"""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Ověří, zda nešifrované heslo odpovídá otisku hesla.
    
    Args:
        plain_password (str): Nešifrované heslo
        hashed_password (str): Hash hesla
        
    Returns:
        bool: True, pokud heslo odpovídá otisku, jinak False
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Vytvoří hash hesla.
    
    Args:
        password (str): Nešifrované heslo
        
    Returns:
        str: Hash hesla
    """
    return pwd_context.hash(password)
