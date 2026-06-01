"""FastAPI 通用依赖。

CurrentUser 仅来自 Cookie (PRD §4.2 — 前端 body/query 中的 user_id 必须忽略)。
本地开发可在 .env 中配置 MOCK_USER_ID 兜底:Cookie 缺失时回退到 mock 身份,生产环境留空即可保持 401 行为。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedError
from app.db.session import get_db
from app.models.user import User


@dataclass(frozen=True)
class CurrentUser:
    """请求上下文中的当前用户视图。"""

    user_id: str
    user_name: str | None
    user_email: str | None


def get_current_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUser:
    """从 Cookie 解析 user_id;Cookie 缺失时若配置了 mock_user_id 则用 mock,否则 401。"""
    user_id = request.cookies.get(settings.cookie_user_id_key)
    user_name = request.cookies.get(settings.cookie_user_name_key)
    user_email = request.cookies.get(settings.cookie_user_email_key)

    if not user_id or not user_id.strip():
        if settings.mock_user_id.strip():
            user_id = settings.mock_user_id.strip()
            user_name = user_name or (settings.mock_user_name or None)
            user_email = user_email or (settings.mock_user_email or None)
        else:
            raise UnauthorizedError("缺少 Cookie 中的 user_id,无法识别登录用户。")
    else:
        user_id = user_id.strip()

    # upsert User 缓存
    user = db.scalar(select(User).where(User.user_id == user_id))
    if user is None:
        user = User(user_id=user_id, user_name=user_name, user_email=user_email)
        db.add(user)
        db.commit()
    else:
        changed = False
        if user_name and user.user_name != user_name:
            user.user_name = user_name
            changed = True
        if user_email and user.user_email != user_email:
            user.user_email = user_email
            changed = True
        if changed:
            db.commit()

    return CurrentUser(user_id=user_id, user_name=user.user_name, user_email=user.user_email)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
DBDep = Annotated[Session, Depends(get_db)]


def get_client_ip(request: Request) -> str:
    """取请求来源 IP,优先 X-Forwarded-For。"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""
