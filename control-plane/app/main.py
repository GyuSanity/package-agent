from fastapi import FastAPI

from app.routers import devices, releases, deployments, agent

app = FastAPI(title="eCode Control Plane", version="0.1.0")

app.include_router(devices.router)
app.include_router(releases.router)
app.include_router(deployments.router)
app.include_router(agent.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
