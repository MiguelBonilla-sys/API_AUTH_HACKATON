from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.auth.jwt_utils import verify_token
from src.config.database import get_db
from src.models.user import User
from src.schemas.auth import TokenData

# Bearer token security scheme
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify token
    payload = verify_token(credentials.credentials, token_type="access")
    if payload is None:
        raise credentials_exception

    # Get user info from token
    user_id: Optional[int] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user (additional check for active status)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current superuser
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


async def get_optional_superuser(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Superuser behind the request's bearer token, or None when there is no token
    or it belongs to a regular user. An invalid token is still rejected.
    """
    if credentials is None:
        return None
    user = await get_current_user(credentials, db)
    return user if user.is_superuser else None


def check_asset_ownership(current_user: User, asset_owner: str) -> bool:
    """
    Check if user can access assets with specific owner
    """
    # Superusers can access everything
    if current_user.is_superuser:
        return True
    
    # Regular users can only access their own assets
    if current_user.dueno_de_activo is None:
        return False
        
    # Normalize strings for comparison (remove extra spaces)
    user_owner = current_user.dueno_de_activo.strip()
    asset_owner_clean = asset_owner.strip()
    
    return user_owner == asset_owner_clean


def verify_asset_access(
    asset_owner: str,
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify that current user can access assets for the given owner
    """
    if not check_asset_ownership(current_user, asset_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a estos activos"
        )
    return current_user