import asyncio

import uvicorn

from backend.core.settings import settings
from backend.core.setup import create_app

app = create_app()


def setup_server() -> uvicorn.Server:
    return uvicorn.Server(
        uvicorn.Config(
            app,
            host=settings.uvicorn.UVICORN_HOST,
            port=settings.uvicorn.UVICORN_PORT,
            loop="uvloop",
            log_config=None,
            proxy_headers=settings.uvicorn.UVICORN_PROXY_HEADERS,
            forwarded_allow_ips=settings.uvicorn.UVICORN_FORWARDED_ALLOW_IPS,
            root_path=settings.uvicorn.UVICORN_ROOT_PATH,
        )
    )


if __name__ == "__main__":
    asyncio.run(setup_server().serve())
