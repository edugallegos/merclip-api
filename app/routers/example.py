from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(
    prefix="/example",
    tags=["example"],
    responses={404: {"description": "Not found"}},
)

class Item(BaseModel):
    id: int
    name: str
    description: str = None

# Example in-memory database
items = [
    Item(id=1, name="Item 1", description="This is item 1"),
    Item(id=2, name="Item 2", description="This is item 2"),
]

@router.get("/", response_model=List[Item])
async def read_items():
    return items

@router.get("/{item_id}", response_model=Item)
async def read_item(item_id: int):
    for item in items:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@router.post("/", response_model=Item)
async def create_item(item: Item):
    items.append(item)
    return item 