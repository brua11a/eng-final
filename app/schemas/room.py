from typing import Optional
from pydantic import BaseModel


class RoomCreateRequest(BaseModel):
    building: str
    room_num: str


class RoomCreateResponse(BaseModel):
    id: int
    building: str
    room_num: str
    err: Optional[str] = None