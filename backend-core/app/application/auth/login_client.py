from __future__ import annotations

from app.application.dtos import LoginClientInput, LoginClientOutput
from app.application.ports.jwt_port import JwtPort
from app.application.ports.password_hasher_port import PasswordHasherPort
from app.domain.client.enums import ClientStatus
from app.domain.client.repository import ClientRepository
from app.domain.shared.errors import (
    AuthError,
    ClientNotApprovedError,
    InvalidCredentialsError,
)
from app.domain.shared.value_objects import Email


class LoginClientUseCase:
    def __init__(
        self,
        client_repo: ClientRepository,
        password_hasher: PasswordHasherPort,
        jwt_handler: JwtPort,
    ) -> None:
        self._repo = client_repo
        self._hasher = password_hasher
        self._jwt = jwt_handler

    async def execute(self, input: LoginClientInput) -> LoginClientOutput:
        try:
            email = Email(input.email)
        except ValueError as exc:
            raise InvalidCredentialsError("Invalid email or password") from exc

        client = await self._repo.find_by_email(email)
        if client is None or client.password_hash is None:
            raise InvalidCredentialsError("Invalid email or password")

        if not self._hasher.verify(input.password, client.password_hash):
            raise InvalidCredentialsError("Invalid email or password")

        if not client.is_active:
            raise AuthError("Account is inactive")

        if client.status == ClientStatus.PENDING:
            raise ClientNotApprovedError("Account is pending approval")

        if client.status == ClientStatus.INACTIVE:
            raise AuthError("Account has been rejected")

        token = self._jwt.sign(
            sub=str(email),
            role=client.role.value,
            client_id=str(client.id),
        )

        return LoginClientOutput(
            access_token=token,
            client_id=str(client.id),
            role=client.role.value,
            status=client.status.value,
        )
