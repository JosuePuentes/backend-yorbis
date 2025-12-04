from pydantic import BaseModel
from typing import Optional

class Example(BaseModel):
    name: str
    description: Optional[str] = None
