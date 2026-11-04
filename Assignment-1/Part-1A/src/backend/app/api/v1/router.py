from fastapi import APIRouter, Depends

from app.api.deps import require_session
from app.api.schemas.common import error_responses
from app.api.v1 import auth, bookings, buses, health, users

# Everything here needs no credential; the gate middleware reads this router as its allow-list.
public_router = APIRouter(prefix="/api/v1")
public_router.include_router(health.router)
public_router.include_router(auth.public_router)

protected_router = APIRouter(
    prefix="/api/v1", dependencies=[Depends(require_session)], responses=error_responses(401)
)
protected_router.include_router(auth.router)
protected_router.include_router(buses.router)
protected_router.include_router(users.router)
protected_router.include_router(bookings.router)

api_router = APIRouter()
api_router.include_router(public_router)
api_router.include_router(protected_router)
