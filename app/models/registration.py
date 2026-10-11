from datetime import date, time
from typing import Literal
from pydantic import BaseModel

RegType = Literal["zapisowa"]


class Registration(BaseModel):
    id: int
    name: str
    reg_type: RegType
    cycle_id: int
    faculty_id: int


class RegistrationTurn(BaseModel):
    id: int
    registration_id: int
    turn_number: int
    date: date
    start_hr: time
    end_time: time
