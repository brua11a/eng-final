from typing import List
from pydantic import BaseModel


class RoomCreateRequest(BaseModel):
    building: str
    room_num: str


class RoomCreateResponse(BaseModel):
    id: str
    building: str
    room_num: str


class RoomItem(BaseModel):
    id: str
    building: str
    room_num: str


class RoomListResponse(BaseModel):
    rooms: List[RoomItem]