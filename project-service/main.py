from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import socket
import os
from consul import Consul
import logging

# === Consul Config ===
CONSUL_HOST = os.getenv("CONSUL_HOST", "localhost")
SERVICE_NAME = os.getenv("SERVICE_NAME", "project-service")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8002))

consul_client = Consul(host=CONSUL_HOST)

# === FastAPI setup ===
app = FastAPI()

# === Model danych ===
class Project(BaseModel):
    id: int
    name: str
    description: str = ""

# Prosta baza danych w pamięci
projects_db = []

# === Consul helper ===
def get_service_ip():
    try:
        return socket.gethostbyname(SERVICE_NAME)
    except:
        return "127.0.0.1"

# === Rejestracja w Consul ===
@app.on_event("startup")
def startup_event():
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
def list_projects():
    return projects_db

@app.post("/projects", response_model=Project)
def add_project(project: Project):
    projects_db.append(project)
    return project

@app.get("/health")
def health_check():
    return {"status": "UP"}
