from dataclasses import dataclass
from typing import Annotated, Any, Literal

from fastapi import Depends, Query
from pydantic import BaseModel

MAX_ID = 2_147_483_647


class HealthOut(BaseModel):
    status: Literal["ok"]


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class Page[T](BaseModel):
    items: list[T]
    page: int
    page_size: int
    total: int


@dataclass(frozen=True)
class PageParams:
    page: int
    page_size: int


def page_params(
    page: Annotated[int, Query(ge=1, le=1_000_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


PageParamsDep = Annotated[PageParams, Depends(page_params)]


# FastAPI types the entries of its `responses` argument as dict[str, Any].
def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI documentation of the shared error body for the given status codes."""
    return {status: {"model": ErrorResponse} for status in statuses}
