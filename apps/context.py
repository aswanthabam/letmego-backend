# core/context.py
from contextvars import ContextVar
import uuid

current_user_id_ctx: ContextVar[uuid.UUID | None] = ContextVar(
    "current_user_id", default=None
)


def set_current_user_id(user_id: uuid.UUID):
    current_user_id_ctx.set(user_id)


def get_current_user_id() -> uuid.UUID | None:
    return current_user_id_ctx.get()
