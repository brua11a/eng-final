from pydantic import BaseModel

class Room(BaseModel):
    id: int
    building: str
    room_num: str