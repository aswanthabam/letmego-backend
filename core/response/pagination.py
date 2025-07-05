from typing import Annotated, Any, Generic, TypeVar, List, Type, Optional, Dict
from urllib.parse import urlencode
from pydantic import BaseModel
from fastapi import Depends, Query as GetQuery, Request
from fastapi.encoders import jsonable_encoder

T = TypeVar("T")
M = TypeVar("M", bound=BaseModel)


class _PaginationParams(BaseModel):
    """Pagination parameters as a Pydantic model"""

    offset: int = 0
    limit: int = 10


def get_pagination_params(
    offset: Annotated[int, GetQuery(ge=0)] = 0,
    limit: Annotated[int, GetQuery(ge=1, le=100)] = 10,
) -> _PaginationParams:
    return _PaginationParams(offset=offset, limit=limit + 1)


class PaginatedResponse(BaseModel, Generic[M]):
    limit: int
    offset: int
    next: Optional[str] = None
    previous: Optional[str] = None
    items: List[M]


def paginated_response(
    result: List[Any], request: Request, schema: Type[M]
) -> PaginatedResponse[M]:
    """
    Create a paginated response from a list of SQLAlchemy models

    Args:
        result: List of SQLAlchemy model instances
        request: FastAPI Request object
        schema: Pydantic model class to convert results into

    Returns:
        PaginatedResponse object with properly formatted items
    """
    limit = int(request.query_params.get("limit", 10))
    offset = int(request.query_params.get("offset", 0))

    # Check if we have more items than requested limit
    has_next = len(result) > limit
    paginated_result = result[:limit] if has_next else result

    has_previous = offset > 0

    # Prepare next URL if we have more results
    if has_next:
        query_params = dict(request.query_params)
        query_params["offset"] = str(offset + limit)
        next_url = f"{request.url.path}?{urlencode(query_params)}"
    else:
        next_url = None

    if has_previous:
        query_params = dict(request.query_params)
        query_params["offset"] = str(max(0, offset - limit))
        previous_url = f"{request.url.path}?{urlencode(query_params)}"
    else:
        previous_url = None

    model_dicts = jsonable_encoder(paginated_result)

    validated_items = [schema.model_validate(item_dict) for item_dict in model_dicts]

    return PaginatedResponse[M](
        limit=limit,
        offset=offset,
        next=next_url,
        previous=previous_url,
        items=validated_items,
    )


PaginationParams = Annotated[_PaginationParams, Depends(get_pagination_params)]
