import logging
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging
from app.modules.agents.router import router as agents_router
from app.modules.audit.router import router as audit_router
from app.modules.authentication.router import router as auth_router
from app.modules.automations.router import router as automations_router
from app.modules.crm.router import router as crm_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.departments.router import router as departments_router
from app.modules.orchestration.router import missions_router, tasks_router
from app.modules.settings.router import router as settings_router
from app.modules.users.router import router as users_router

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
logger = logging.getLogger("persomy")


def origin_of(value: str) -> str:
    parsed = urlparse(value)
    return f"{parsed.scheme}://{parsed.netloc}"


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info("persomy-api started env=%s", settings.app_env)
        yield

    docs_enabled = settings.app_env != "production"
    app = FastAPI(
        title="Persomy AI API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if docs_enabled else None,
    )
    register_error_handlers(app)

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        # Défense en profondeur CSRF : une requête modifiante portant un en-tête Origin
        # doit provenir d'une origine de confiance.
        if request.method not in SAFE_METHODS:
            origin = request.headers.get("origin")
            if origin and origin_of(origin) not in {origin_of(o) for o in get_settings().trusted_origins}:
                return JSONResponse(
                    status_code=403,
                    content={"error": {"code": "origin_not_allowed", "message": "Origin not allowed"}},
                )
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        return response

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def ready(db: Session = Depends(get_db)):
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
        return {"status": "ok", "database": "ok"}

    for router in (
        auth_router,
        users_router,
        audit_router,
        settings_router,
        dashboard_router,
        departments_router,
        automations_router,
        crm_router,
        agents_router,
        missions_router,
        tasks_router,
    ):
        app.include_router(router, prefix="/api/v1")
    return app


app = create_app()
