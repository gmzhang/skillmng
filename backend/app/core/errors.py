"""业务异常 + FastAPI 全局处理器。"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class BusinessError(Exception):
    """业务异常基类,带 HTTP 状态码与错误码。"""

    status_code: int = 400
    code: str = "business_error"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(BusinessError):
    status_code = 404
    code = "not_found"


class ValidationError(BusinessError):
    status_code = 422
    code = "validation_error"


class ConflictError(BusinessError):
    status_code = 409
    code = "conflict"


class UnauthorizedError(BusinessError):
    status_code = 401
    code = "unauthorized"


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def _business_handler(_: Request, exc: BusinessError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )
