from pydantic import BaseModel, Field
from typing import Optional

class UserCreate(BaseModel):
    full_name: str
    class_id: int
    pin: str = Field(..., min_length=4, max_length=4, description="4-значный ПИН")

class UserLogin(BaseModel):
    full_name: str
    class_id: int
    pin: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    class_id: Optional[int] = None
    role: str

    class Config:
        from_attributes = True

class TeacherLogin(BaseModel):
    username: str
    password: str
