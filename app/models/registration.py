from datetime import date, time
from typing import Literal
from pydantic import BaseModel

RegType = Literal["zapisowa", "poprawkowa"]


class Registration(BaseModel):
    id: int
    turn_number: int
    reg_type: RegType
    date: date
    start_hr: time
    end_time: time
    cycle_id: int
    faculty_id: int
