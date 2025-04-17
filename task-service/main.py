from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# === DB CONFIG ===
DATABASE_URL = "postgresql://user:password@task-db:5432/taskdb"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# === ORM MODEL ===
class TaskORM(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    project_id = Column(Integer)
    is_done = Column(Boolean, default=False)

# === Pydantic model ===
class Task(BaseModel):
    id: int
    title: str
    description: str = ""
    project_id: int
    is_done: bool = False

    class Config:
        orm_mode = True

# === FASTAPI SETUP ===
app = FastAPI()

# Tworzenie tabel przy starcie
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# Dependency: sesja DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === ENDPOINTY ===

@app.get("/tasks", response_model=List[Task])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(TaskORM).all()

@app.post("/tasks", response_model=Task)
def create_task(task: Task, db: Session = Depends(get_db)):
    db_task = TaskORM(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: Task, db: Session = Depends(get_db)):
    db_task = db.query(TaskORM).filter(TaskORM.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in task.dict().items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.query(TaskORM).filter(TaskORM.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    return {"message": "Task deleted"}
