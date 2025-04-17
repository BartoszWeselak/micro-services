from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from datetime import datetime

app = FastAPI()

class ScheduleItem(BaseModel):
    id: int
    title: str
    datetime: datetime
    description: str
    related_task_id: int

schedule_items: List[ScheduleItem] = []

@app.get("/schedule", response_model=List[ScheduleItem])
def get_schedule():
    return schedule_items

@app.post("/schedule", response_model=ScheduleItem)
def add_schedule_item(item: ScheduleItem):
    schedule_items.append(item)
    return item

@app.delete("/schedule/{item_id}")
def delete_schedule_item(item_id: int):
    global schedule_items
    schedule_items = [item for item in schedule_items if item.id != item_id]
    return {"message": "Schedule item deleted"}
