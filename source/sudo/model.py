from typing import Optional
from pydantic import BaseModel


class SudokuCreate(BaseModel):
    name: str
    puzzle: str
    difficulty: Optional[str] = None
    answer: Optional[str] = None
    type: Optional[str] = None


class SudokuUpdate(BaseModel):
    name: Optional[str] = None
    puzzle: Optional[str] = None
    difficulty: Optional[str] = None
    answer: Optional[str] = None
    type: Optional[str] = None
