from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from app.api.deps import AuthServiceDep, CurrentUserDep
from app.api.error_handlers import response_for
from app.api.schemas.auth import BEARER, AuthUser, LoginRequest, LoginResponse
from app.api.schemas.common import error_responses
from app.services.types import LoginRejected

public_router = APIRouter(prefix="/auth", tags=["auth"])
router = APIRouter(prefix="/auth", tags=["auth"])


@public_router.post(
    "/login", response_model=LoginResponse, responses=error_responses(401, 422, 429, 503)
)
def login(payload: LoginRequest, service: AuthServiceDep) -> LoginResponse | JSONResponse:
    result = service.login(payload.username, payload.password)
    if isinstance(result, LoginRejected):
        return response_for(result.error)
    return LoginResponse(
        access_token=result.access_token,
        token_type=BEARER,
        expires_at=result.expires_at,
        user=AuthUser(id=result.user_id, name=result.name),
    )


@router.get("/me", response_model=AuthUser, responses=error_responses(401, 503))
def me(current_user: CurrentUserDep) -> AuthUser:
    return AuthUser(id=current_user.user_id, name=current_user.name)


@router.post(
    "/logout", status_code=204, response_class=Response, responses=error_responses(401, 503)
)
def logout(current_user: CurrentUserDep, service: AuthServiceDep) -> Response:
    service.logout(current_user)
    return Response(status_code=204)
