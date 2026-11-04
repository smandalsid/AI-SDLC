from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BEARER: Literal["bearer"] = "bearer"


class LoginRequest(BaseModel):
    # Values are kept exactly as typed and never echoed back in validation errors.
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class AuthUser(BaseModel):
    id: int
    name: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    expires_at: datetime
    user: AuthUser
