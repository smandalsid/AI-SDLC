from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SessionDep
from app.api.schemas.common import HealthOut, error_responses

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def liveness() -> HealthOut:
    return HealthOut(status="ok")


@router.get("/ready", responses=error_responses(503))
def readiness(session: SessionDep) -> HealthOut:
    session.execute(text("SELECT 1"))
    return HealthOut(status="ok")
