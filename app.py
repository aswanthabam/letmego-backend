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

from apps.settings import settings
from avcfastapi.core.fastapi.app import create_app


async def on_startup():
    print("Application Starting Up ...")


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("Application Starting Up ...")
#     yield
#     print("application closing")

app = create_app(apps_dir="apps", on_startup=on_startup)


@app.get("/api/ping", summary="Ping the API", tags=["Health Check"])
def root():
    return HTMLResponse(content="<html><h1>Haa shit! My Code is working.</h1></html>")
