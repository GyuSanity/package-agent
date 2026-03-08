"""
Base repository utilities for common DB operations.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_by_id(db: AsyncSession, model, record_id):
    result = await db.execute(select(model).where(model.id == record_id))
    return result.scalar_one_or_none()


async def get_all(db: AsyncSession, model, filters: dict | None = None):
    stmt = select(model)
    if filters:
        for key, value in filters.items():
            if value is not None:
                stmt = stmt.where(getattr(model, key) == value)
    result = await db.execute(stmt)
    return result.scalars().all()
