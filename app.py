from contextlib import asynccontextmanager
import traceback
import uuid
from fastapi import Request
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import HTMLResponse
from sqlalchemy.exc import StatementError, IntegrityError

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from apps.settings import settings
from avcfastapi.core.fastapi.app import create_app


# Rate limiter: 60 requests/minute for authenticated, 30/min for public endpoints
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])


async def on_startup():
    print("Application Starting Up ...")


app = create_app(apps_dir="apps", on_startup=on_startup)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/api/ping", summary="Ping the API", tags=["Health Check"])
def root():
    return HTMLResponse(content="<html><h1>LetMeGo API is running.</h1></html>")

