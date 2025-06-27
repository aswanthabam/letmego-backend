from fastapi import APIRouter

router = APIRouter(
    prefix="",
    responses={404: {"description": "Not found"}},
)
