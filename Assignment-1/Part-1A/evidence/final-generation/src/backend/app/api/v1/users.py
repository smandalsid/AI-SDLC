from fastapi import APIRouter

from app.api.deps import UserServiceDep
from app.api.schemas.common import PageParamsDep, error_responses
from app.api.schemas.user import UserOut, UserPage

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserPage, responses=error_responses(422, 503))
def list_users(params: PageParamsDep, service: UserServiceDep) -> UserPage:
    result = service.list_users(params.page, params.page_size)
    return UserPage(
        items=[UserOut.model_validate(user) for user in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )
