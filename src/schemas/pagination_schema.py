import math
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, skip: int, limit: int):
        pages = math.ceil(total / limit) if limit > 0 else 0
        current_page = (skip // limit) + 1 if total > 0 and limit > 0 else 0
        return cls(
            items=items,
            total=total,
            page=current_page,
            size=limit,
            pages=pages,
        )
