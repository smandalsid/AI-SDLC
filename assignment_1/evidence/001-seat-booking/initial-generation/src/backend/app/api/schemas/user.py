from pydantic import BaseModel, ConfigDict

from app.api.schemas.common import Page


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class UserPage(Page[UserOut]):
    pass
