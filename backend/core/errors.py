from authx import JWTDecodeError
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from backend.auth.security import auth


def setup_auth_errors(app: FastAPI) -> None:
    auth.handle_errors(app)

    @app.exception_handler(JWTDecodeError)
    async def jwt_decode_error_handler(
        request: Request, exc: JWTDecodeError
    ) -> JSONResponse:
        name = exc.__class__.__name__
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "message": getattr(auth, f"MSG_{name}", None) or str(exc),
                "error_type": name,
            },
        )
