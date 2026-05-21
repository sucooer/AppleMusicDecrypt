from __future__ import annotations

from src.grpc.manager import WrapperManagerException
from src.web.schemas import AuthResponse


class WebAuthService:
    def __init__(self, wrapper_manager) -> None:
        self._wrapper_manager = wrapper_manager

    async def login(self, username: str, password: str, two_step_code: str | None = None) -> AuthResponse:
        async def provide_2fa(_username: str, _password: str) -> str:
            if not two_step_code:
                raise WrapperManagerException("2FA code required")
            return two_step_code

        try:
            await self._wrapper_manager.login(username, password or "", provide_2fa)
        except WrapperManagerException as exc:
            if "2FA" in exc.msg or "2FA code required" in exc.msg:
                return AuthResponse(status="need_2fa", message=str(exc.msg))
            if "already login" in exc.msg:
                return AuthResponse(status="failed", message="该账号已登录。如需切换，请先清除当前账号。")
            return AuthResponse(status="failed", message=str(exc.msg))
        return AuthResponse(status="success", message="Login success")

    async def logout(self, username: str) -> AuthResponse:
        try:
            await self._wrapper_manager.logout(username)
        except WrapperManagerException as exc:
            return AuthResponse(status="failed", message=str(exc.msg))
        return AuthResponse(status="success", message="Logout success")
