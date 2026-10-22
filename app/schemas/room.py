from typing import List, Optional
from pydantic import BaseModel


class RoomCreateRequest(BaseModel):
    building: str
    room_num: str


class RoomCreateResponse(BaseModel):
    id: int
    building: str
    room_num: str
    err: Optional[str] = None


class RoomItem(BaseModel):
    id: int
    building: str
    room_num: str


class RoomListResponse(BaseModel):
    rooms: List[RoomItem]