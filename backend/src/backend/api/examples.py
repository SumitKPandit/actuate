"""Placeholder CRUD proving the `get_db` session pattern."""

from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.example import Example

router = APIRouter(prefix="/examples", tags=["examples"])


class ExampleCreate(BaseModel):
    content: str = Field(min_length=1, max_length=280)


class ExampleRead(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    content: str
    created_at: datetime


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_example(
    payload: ExampleCreate, db: AsyncSession = Depends(get_db)  # noqa: B008
) -> ExampleRead:
    row = Example(content=payload.content)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ExampleRead.model_validate(row)


@router.get("")
async def list_examples(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> list[ExampleRead]:
    res = await db.execute(select(Example).order_by(Example.id).limit(100))
    return [ExampleRead.model_validate(r) for r in res.scalars()]
