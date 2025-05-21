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
import requests


# === Consul Config ===
CONSUL_HOST = os.getenv("CONSUL_HOST", "localhost")
SERVICE_NAME = os.getenv("SERVICE_NAME", "project-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8002))

consul_client = Consul(host=CONSUL_HOST)

# === DB CONFIG ===
DATABASE_URL = "postgresql://user:password@project-db:5432/projectdb"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# === ORM MODEL ===
class ProjectORM(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    description = Column(String, default="")


# === Pydantic model ===
class Project(BaseModel):
    id: int | None = None
    name: str
    description: str = ""

    class Config:
        orm_mode = True


# === FastAPI setup ===
app = FastAPI()

def discover_service(service_name: str):
    try:
        services = consul_client.agent.services()
        for service in services.values():
            if service["Service"] == service_name:
                address = service["Address"]
                port = service["Port"]
                return f"http://{address}:{port}"
    except Exception as e:
        logging.error(f"Service discovery error: {str(e)}")
    return None
def get_service_ip():
    try:
        return socket.gethostbyname(SERVICE_NAME)
    except:
        return "127.0.0.1"


# Tworzenie tabel przy starcie
@app.on_event("startup")
def startup_event():
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
        logging.info(f"Zarejestrowano {SERVICE_NAME} w Consul")
    except Exception as e:
        logging.error(f"Błąd rejestracji w Consul: {str(e)}")


# Dependency: sesja DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# === Endpointy ===
@app.get("/projects", response_model=List[Project])
def list_projects(db: Session = Depends(get_db)):
    return db.query(ProjectORM).all()


@app.post("/projects", response_model=Project)
def add_project(project: Project, db: Session = Depends(get_db)):
    db_project = ProjectORM(**project.dict(exclude={"id"}))
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@app.put("/projects/{project_id}", response_model=Project)
def update_project(project_id: int, project: Project, db: Session = Depends(get_db)):
    db_project = db.query(ProjectORM).filter(ProjectORM.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in project.dict().items():
        if key != "id":
            setattr(db_project, key, value)

    db.commit()
    db.refresh(db_project)
    return db_project


@app.delete("/projects/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    db_project = db.query(ProjectORM).filter(ProjectORM.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(db_project)
    db.commit()
    return {"message": "Project deleted successfully"}

@app.delete("/projects/{project_id}/with-tasks")
def delete_project_and_tasks(project_id: int, db: Session = Depends(get_db)):
    project = db.query(ProjectORM).filter(ProjectORM.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # odkrycie task-service
    task_service_url = discover_service("task-service")
    if not task_service_url:
        raise HTTPException(status_code=500, detail="Task service unavailable")

    # DELETE na task-service
    try:
        response = requests.delete(f"{task_service_url}/tasks/by-project/{project_id}")
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to delete related tasks")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting tasks: {str(e)}")

    # usunięcie projektu
    db.delete(project)
    db.commit()

    return {"message": f"Project {project_id} and its tasks were deleted"}

@app.get("/health")
def health_check():
    return {"status": "UP"}


# === Wyrejestrowanie ===
@app.on_event("shutdown")
async def shutdown_event():
    service_ip = get_service_ip()
    service_id = f"{SERVICE_NAME}-{service_ip}-{SERVICE_PORT}"
    try:
        consul_client.agent.service.deregister(service_id)
        logging.info(f"Wyrejestrowano {SERVICE_NAME} z Consul")
    except Exception as e:
        logging.error(f"Błąd wyrejestrowania z Consul: {str(e)}")