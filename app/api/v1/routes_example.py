from fastapi import APIRouter
from app.models.example_model import Example
from app.services.example_service import create_example, get_all_examples

router = APIRouter()

@router.post("/example")
async def add_example(example: Example):
    return await create_example(example)

@router.get("/examples")
async def list_examples():
    return await get_all_examples()
