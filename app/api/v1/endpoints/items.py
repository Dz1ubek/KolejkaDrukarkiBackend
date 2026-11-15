from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, HTTPException, status
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate

router = APIRouter(prefix="/items", tags=["Items"])

# Simple in-memory storage for demonstration purposes
_ITEMS_DB: List[dict] = [
    {
        "id": 1,
        "title": "Sample 3D Print Job",
        "description": "Benchy 3D calibration print",
        "is_completed": False,
        "created_at": datetime.now(timezone.utc),
    }
]
_NEXT_ID = 2


@router.get("", response_model=List[ItemResponse], summary="List all items")
def list_items():
    """Retrieve all items."""
    return _ITEMS_DB


@router.get("/{item_id}", response_model=ItemResponse, summary="Get item by ID")
def get_item(item_id: int):
    """Retrieve a single item by its ID."""
    for item in _ITEMS_DB:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED, summary="Create a new item")
def create_item(payload: ItemCreate):
    """Create a new item."""
    global _NEXT_ID
    new_item = {
        "id": _NEXT_ID,
        "title": payload.title,
        "description": payload.description,
        "is_completed": payload.is_completed,
        "created_at": datetime.now(timezone.utc),
    }
    _NEXT_ID += 1
    _ITEMS_DB.append(new_item)
    return new_item


@router.put("/{item_id}", response_model=ItemResponse, summary="Update an item")
def update_item(item_id: int, payload: ItemUpdate):
    """Update fields of an existing item."""
    for item in _ITEMS_DB:
        if item["id"] == item_id:
            update_data = payload.model_dump(exclude_unset=True)
            item.update(update_data)
            return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an item")
def delete_item(item_id: int):
    """Delete an item by its ID."""
    for index, item in enumerate(_ITEMS_DB):
        if item["id"] == item_id:
            _ITEMS_DB.pop(index)
            return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
