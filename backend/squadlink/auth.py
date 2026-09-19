"""Email/password auth via fastapi-users, JWT bearer tokens. (Google OAuth can be added as another router later.)"""

import uuid

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, InvalidPasswordException, UUIDIDMixin, schemas
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from .db import User, get_session

MIN_PASSWORD_LENGTH = 8


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    async def validate_password(self, password: str, user) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidPasswordException(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(request: Request, user_db=Depends(get_user_db)):
    manager = UserManager(user_db)
    manager.reset_password_token_secret = request.app.state.settings.auth_secret
    manager.verification_token_secret = request.app.state.settings.auth_secret
    yield manager


def get_jwt_strategy(request: Request) -> JWTStrategy:
    s = request.app.state.settings
    return JWTStrategy(secret=s.auth_secret, lifetime_seconds=s.jwt_lifetime_seconds)


auth_backend = AuthenticationBackend(
    name="jwt", transport=BearerTransport(tokenUrl="auth/jwt/login"), get_strategy=get_jwt_strategy
)
fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])
current_user = fastapi_users.current_user(active=True)
