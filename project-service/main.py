# project-service/main.py
from fastapi import FastAPI

app = FastAPI()

projects = []

@app.get("/projects")
def get_projects():
    return projects

@app.post("/projects")
def create_project(name: str):
    project = {"id": len(projects) + 1, "name": name}
    projects.append(project)
    return project
