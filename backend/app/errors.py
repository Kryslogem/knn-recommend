"""Lỗi thống nhất: {"detail": "...", "code": "..."} cho 400/401/403/404/409/422/503."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(self, status: int, code: str, detail: str):
        self.status, self.code, self.detail = status, code, detail


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, e: AppError):
        return JSONResponse({"detail": e.detail, "code": e.code}, status_code=e.status)

    @app.exception_handler(HTTPException)
    async def _http(_: Request, e: HTTPException):
        detail = e.detail if isinstance(e.detail, str) else "Yêu cầu không hợp lệ"
        return JSONResponse({"detail": detail, "code": f"http_{e.status_code}"}, status_code=e.status_code, headers=e.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        errors = [
            {"field": ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path")), "message": err["msg"]}
            for err in e.errors()
        ]
        first = errors[0] if errors else {"field": "", "message": ""}
        return JSONResponse(
            {"detail": f"Dữ liệu không hợp lệ ({first['field']}): {first['message']}", "code": "validation_error", "errors": errors},
            status_code=422,
        )
