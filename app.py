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

from core.exceptions.core import AbstractException
from core.response.response_class import CustomORJSONResponse
from core.loaders.router import autoload_routers
from core.middlewares.process_time_middleware import ProcessingTimeMiddleware
from apps.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application Starting Up ...")
    yield
    print("application closing")


app = FastAPI(lifespan=lifespan, default_response_class=CustomORJSONResponse)

router = autoload_routers("apps")

app.include_router(router=router)

app.add_middleware(ProcessingTimeMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AbstractException)
async def abstract_exception_handler(request: Request, exc: AbstractException):
    return ORJSONResponse(exc.to_json(), status_code=exc.status_code)


async def custom_auth_exception_handler(request: Request, exc: Exception):
    return ORJSONResponse(
        {
            "message": "Unauthorized!",
            "error_code": "UNAUTHORIZED",
        },
        status_code=401,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "type": error.get("type", "unknown"),
                "loc": error.get("loc", []),
                "msg": error.get("msg", "Invalid input"),
                "input": error.get("input", None),
            }
        )
    return ORJSONResponse(
        {
            "message": "Invalid Request, Please check your request",
            "error_code": "REQUEST_VALIDATION_ERROR",
            "errors": errors,
        },
        status_code=422,
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return ORJSONResponse(
        {
            "message": "Error Processing Request",
            "error_code": "VALIDATION_ERROR",
            "errors": {"msg": f"{e.get('loc')} {e.get('msg')}" for e in exc.errors()},
        },
        status_code=500,
    )


@app.exception_handler(StatementError)
async def statement_error_handler(request: Request, exc: StatementError):
    if isinstance(exc.orig, AbstractException):
        raise exc.orig
    else:
        raise exc


@app.exception_handler(IntegrityError)
async def statement_error_handler(request: Request, exc: IntegrityError):
    traceback.print_exc()
    return ORJSONResponse(
        {
            "message": "Integrity Error",
            "error_code": "INTEGRITY_ERROR",
        },
    )


@app.exception_handler(Exception)
async def http_exception_handler(request: Request, exc: Exception):
    track_id = str(uuid.uuid4())
    # try:
    #     await notify_error(request, exc, track_id)
    # except Exception as e:
    #     print("Error while sending error notification")
    #     traceback.print_exc()
    return ORJSONResponse(
        {
            "message": "Error Processing Request",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
        status_code=500,
    )


app.add_exception_handler(401, custom_auth_exception_handler)


@app.get("/api/ping", summary="Ping the API", tags=["Health Check"])
def root():
    return HTMLResponse(content="<html><h1>Haa shit! My Code is working.</h1></html>")
