from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from consul import Consul
import logging
import socket
from typing import Optional

# === Consul Client Setup ===
CONSUL_HOST = os.getenv("CONSUL_HOST", "localhost")
SERVICE_NAME = os.getenv("SERVICE_NAME", "task-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8001))

consul_client = Consul(host=CONSUL_HOST)

# === DB CONFIG ===
DATABASE_URL = "postgresql://user:password@task-db:5432/taskdb"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()



# === ORM MODEL ===
class TaskORM(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String)
    project_id = Column(Integer, nullable=True)
    is_done = Column(Boolean, default=False)

# === Pydantic model ===
class Task(BaseModel):
    id: int | None = None
    title: str
    description: str = ""
    project_id: Optional[int] = None
    is_done: bool = False

    class Config:
        orm_mode = True

# === FASTAPI SETUP ===
app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def discover_service(service_name: str):
    try:
        services = consul_client.agent.services()
        for service in services.values():
            if service['Service'] == service_name:
                address = service['Address']
                port = service['Port']
                return f"http://{address}:{port}"
    except Exception as e:
        logging.error(f"Service discovery error: {str(e)}")
    return None

@app.delete("/tasks/by-project/{project_id}")
def delete_tasks_by_project(project_id: int, db: Session = Depends(get_db)):
    tasks = db.query(TaskORM).filter(TaskORM.project_id == project_id).all()
    if not tasks:
        return {"message": "No tasks found for this project"}
    for task in tasks:
        db.delete(task)
    db.commit()
    return {"message": f"Deleted {len(tasks)} tasks for project {project_id}"}

@app.patch("/tasks/unassign/{project_id}")
def unassign_tasks(project_id: int, db: Session = Depends(get_db)):
    tasks = db.query(TaskORM).filter(TaskORM.project_id == project_id).all()
    for task in tasks:
        task.project_id = None
    db.commit()
    return {"message": f"{len(tasks)} tasks unassigned from project {project_id}"}

def get_service_ip():
    try:
        return socket.gethostbyname(SERVICE_NAME)
    except:
        return "127.0.0.1"
# Tworzenie tabel przy starcie
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    # Rejestracja w Consul
    service_ip = get_service_ip()
    service_id = f"{SERVICE_NAME}-{service_ip}-{SERVICE_PORT}"

    try:
        consul_client.agent.service.register(
            name=SERVICE_NAME,
            service_id=service_id,
            address=service_ip,
            port=SERVICE_PORT,
            check={
                "name": "HTTP API Check",
                "http": f"http://{service_ip}:{SERVICE_PORT}/health",
                "interval": "10s",
                "timeout": "5s"
            }
        )
        logging.info(f"Successfully registered with Consul as {SERVICE_NAME}")
    except Exception as e:
        logging.error(f"Failed to register with Consul: {str(e)}")
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

import requests


@app.post("/tasks", response_model=Task)
def create_task(task: Task, db: Session = Depends(get_db)):
    task_data = task.dict(exclude={"id"})

    if task.project_id is not None:  # ← warunkowa walidacja
        project_service_url = discover_service("project-service")
        if not project_service_url:
            raise HTTPException(status_code=500, detail="Project service unavailable")

        try:
            response = requests.get(f"{project_service_url}/projects")
            if response.status_code == 200:
                projects = response.json()
                if not any(p["id"] == task.project_id for p in projects):
                    raise HTTPException(status_code=400, detail="Project does not exist")
            else:
                raise HTTPException(status_code=500, detail="Failed to validate project")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    db_task = TaskORM(**task_data)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task: Task, db: Session = Depends(get_db)):
    db_task = db.query(TaskORM).filter(TaskORM.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.project_id is not None:
        project_service_url = discover_service("project-service")
        if not project_service_url:
            raise HTTPException(status_code=500, detail="Project service unavailable")

        try:
            response = requests.get(f"{project_service_url}/projects")
            if response.status_code == 200:
                projects = response.json()
                if not any(p["id"] == task.project_id for p in projects):
                    raise HTTPException(status_code=400, detail="Project does not exist")
            else:
                raise HTTPException(status_code=500, detail="Failed to validate project")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    for key, value in task.dict().items():
        if key != "id":
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


@app.on_event("shutdown")
async def shutdown_event():
    service_ip = get_service_ip()
    service_id = f"{SERVICE_NAME}-{service_ip}-{SERVICE_PORT}"

    try:
        consul_client.agent.service.deregister(service_id)
        logging.info("Successfully unregistered from Consul")
    except Exception as e:
        logging.error(f"Failed to unregister from Consul: {str(e)}")

# Health check endpoint wymagany przez Consul
@app.get("/health")
def health_check():
    return {"status": "UP"}