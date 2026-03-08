import uuid

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.schemas import DeploymentCreate, DeploymentOut
from app.services import deployment_service

router = APIRouter(prefix="/api/v1/deployments", tags=["deployments"])


@router.post("", response_model=DeploymentOut, status_code=status.HTTP_201_CREATED)
async def create_deployment(body: DeploymentCreate, db: AsyncSession = Depends(get_db)):
    deployment = await deployment_service.create_deployment(db, body)
    return deployment


@router.get("", response_model=list[DeploymentOut])
async def list_deployments(db: AsyncSession = Depends(get_db)):
    deployments = await deployment_service.list_deployments(db)
    return deployments


@router.get("/{deployment_id}", response_model=DeploymentOut)
async def get_deployment(deployment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    deployment = await deployment_service.get_deployment(db, deployment_id)
    if deployment is None:
        return JSONResponse(status_code=404, content={"detail": "Deployment not found"})
    return deployment
