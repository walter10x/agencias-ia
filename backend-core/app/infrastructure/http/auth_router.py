from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.application.auth.login_client import LoginClientUseCase
from app.application.auth.register_client import RegisterClientUseCase
from app.application.dtos import LoginClientInput, RegisterClientInput
from app.domain.shared.errors import (
    AuthError,
    ClientNotApprovedError,
    EmailAlreadyRegisteredError,
    InvalidClientError,
    InvalidCredentialsError,
    WeakPasswordError,
)
from app.infrastructure.http.dependencies import (
    get_client_repo,
    get_current_client,
    get_jwt_handler,
    get_password_hasher,
)
from app.infrastructure.http.schemas import (
    CurrentClientResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.infrastructure.persistence.client_repository import SupabaseClientRepository
from app.infrastructure.security.jwt_handler import JoseJwtHandler
from app.infrastructure.security.password_hasher import BcryptPasswordHasher

router = APIRouter()


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    repo: SupabaseClientRepository = Depends(get_client_repo),
    hasher: BcryptPasswordHasher = Depends(get_password_hasher),
) -> RegisterResponse:
    uc = RegisterClientUseCase(repo, hasher)
    inp = RegisterClientInput(
        email=body.email,
        password=body.password,
        business_name=body.business_name,
        whatsapp_number=body.whatsapp_number,
    )
    try:
        output = await uc.execute(inp)
    except WeakPasswordError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except EmailAlreadyRegisteredError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except InvalidClientError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return RegisterResponse(
        client_id=output.client_id,
        email=output.email,
        status=output.status,
        message=output.message,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    repo: SupabaseClientRepository = Depends(get_client_repo),
    hasher: BcryptPasswordHasher = Depends(get_password_hasher),
    jwt: JoseJwtHandler = Depends(get_jwt_handler),
) -> LoginResponse:
    uc = LoginClientUseCase(repo, hasher, jwt)
    inp = LoginClientInput(email=body.email, password=body.password)
    try:
        output = await uc.execute(inp)
    except InvalidCredentialsError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except ClientNotApprovedError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except AuthError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return LoginResponse(
        access_token=output.access_token,
        client_id=output.client_id,
        role=output.role,
        status=output.status,
    )


@router.get("/me", response_model=CurrentClientResponse)
async def me(
    current: CurrentClientResponse = Depends(get_current_client),  # type: ignore[assignment]
) -> CurrentClientResponse:
    return current
