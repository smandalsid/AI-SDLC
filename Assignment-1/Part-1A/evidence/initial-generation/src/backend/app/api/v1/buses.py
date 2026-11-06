from typing import Annotated

from fastapi import APIRouter, Path

from app.api.deps import BusServiceDep
from app.api.schemas.bus import BusDetailOut, BusOut, BusPage
from app.api.schemas.common import MAX_ID, PageParamsDep, error_responses

router = APIRouter(prefix="/buses", tags=["buses"])


@router.get("", response_model=BusPage, responses=error_responses(422, 503))
def list_buses(params: PageParamsDep, service: BusServiceDep) -> BusPage:
    result = service.list_buses(params.page, params.page_size)
    return BusPage(
        items=[BusOut.model_validate(bus) for bus in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
    )


@router.get("/{bus_id}", response_model=BusDetailOut, responses=error_responses(404, 422, 503))
def get_bus(bus_id: Annotated[int, Path(ge=1, le=MAX_ID)], service: BusServiceDep) -> BusDetailOut:
    return BusDetailOut.model_validate(service.get_bus_detail(bus_id))
