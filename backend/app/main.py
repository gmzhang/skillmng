"""FastAPI 应用入口。"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import antcode, files, importexport, llm, me, settings_api, skills, versions
from app.core.config import get_settings
from app.core.errors import install_exception_handlers
from app.core.logging import init_logging

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app() -> FastAPI:
    init_logging()
    settings = get_settings()

    app = FastAPI(title="Skill 管理系统", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_exception_handlers(app)

    app.include_router(me.router, prefix="/api", tags=["me"])
    app.include_router(skills.router, prefix="/api/skills", tags=["skills"])
    app.include_router(llm.router, prefix="/api/llm", tags=["llm"])
    app.include_router(importexport.router, prefix="/api", tags=["import"])
    app.include_router(importexport.audit_router, prefix="/api/audit-logs", tags=["audit"])
    app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])

    files_parent = APIRouter()
    files_parent.include_router(files.router, prefix="/{skill_id}/files")
    files_parent.include_router(versions.router, prefix="/{skill_id}/versions")
    files_parent.include_router(versions.diff_router, prefix="/{skill_id}")
    files_parent.include_router(importexport.export_router, prefix="/{skill_id}")
    files_parent.include_router(antcode.router, prefix="/{skill_id}")
    app.include_router(files_parent, prefix="/api/skills", tags=["nested"])

    if STATIC_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static-assets")

        @app.get("/{full_path:path}")
        async def serve_spa(request: Request, full_path: str):
            file_path = STATIC_DIR / full_path
            if file_path.is_file():
                return FileResponse(file_path)
            return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
