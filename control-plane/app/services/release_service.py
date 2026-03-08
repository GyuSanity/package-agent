import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Release, ReleaseService
from app.schemas.schemas import ReleaseCreate


async def create_release(db: AsyncSession, data: ReleaseCreate) -> Release:
    release = Release(
        id=uuid.uuid4(),
        release_name=data.release_name,
        robot_model=data.robot_model,
        status="draft",
        created_by=data.created_by,
        created_at=datetime.utcnow(),
    )
    db.add(release)

    for svc in data.services:
        rs = ReleaseService(
            id=uuid.uuid4(),
            release_id=release.id,
            service_name=svc.service_name,
            image_repo=svc.image_repo,
            image_tag=svc.image_tag,
            image_digest=svc.image_digest,
            healthcheck_profile=svc.healthcheck_profile,
            created_at=datetime.utcnow(),
        )
        db.add(rs)

    await db.commit()
    await db.refresh(release)
    return release


async def list_releases(db: AsyncSession, robot_model: str | None = None, status: str | None = None) -> list[Release]:
    stmt = select(Release)
    if robot_model is not None:
        stmt = stmt.where(Release.robot_model == robot_model)
    if status is not None:
        stmt = stmt.where(Release.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_release(db: AsyncSession, release_id: uuid.UUID) -> Release | None:
    result = await db.execute(select(Release).where(Release.id == release_id))
    return result.scalar_one_or_none()
