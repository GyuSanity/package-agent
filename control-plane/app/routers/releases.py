import uuid
from typing import Optional

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.schemas import ReleaseCreate, ReleaseOut
from app.services import release_service

router = APIRouter(prefix="/api/v1/releases", tags=["releases"])


@router.post("", response_model=ReleaseOut, status_code=status.HTTP_201_CREATED)
async def create_release(body: ReleaseCreate, db: AsyncSession = Depends(get_db)):
    release = await release_service.create_release(db, body)
    return release


@router.get("", response_model=list[ReleaseOut])
async def list_releases(
    robot_model: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    releases = await release_service.list_releases(db, robot_model=robot_model, status=status_filter)
    return releases


@router.get("/{release_id}", response_model=ReleaseOut)
async def get_release(release_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    release = await release_service.get_release(db, release_id)
    if release is None:
        return JSONResponse(status_code=404, content={"detail": "Release not found"})
    return release
