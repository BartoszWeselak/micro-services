from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os
from consul import Consul
import logging
import socket

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


@app.get("/health")
def health_check():
    return {"status": "UP"}