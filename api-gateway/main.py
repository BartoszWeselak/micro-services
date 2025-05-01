from fastapi import FastAPI, Request, HTTPException
import httpx
import os
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Form

app = FastAPI()

SERVICE_MAP = {
    "tasks": "http://task-service:8001",
    "projects": "http://project-service:8002",
    "communication": "http://communication-service:8005",
    "report": "http://report-service:8003",
    "schedule": "http://schedule-service:8004",
}
templates = Jinja2Templates(directory="templates")
# app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    try:
        async with httpx.AsyncClient() as client:
            task_response = await client.get(f"{SERVICE_MAP['tasks']}/tasks")
            project_response = await client.get(f"{SERVICE_MAP['projects']}/projects")
            tasks = task_response.json()
            projects = project_response.json()
    except Exception as e:
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)})

    return templates.TemplateResponse("index.html", {
        "request": request,
        "tasks": tasks,
        "projects": projects
    })

@app.post("/add-task", response_class=RedirectResponse)
async def add_task(title: str = Form(...), description: str = Form(""), project_id: int = Form(...)):
    task_data = {
        "title": title,
        "description": description,
        "project_id": project_id,
        "is_done": False
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{SERVICE_MAP['tasks']}/tasks", json=task_data)
            response.raise_for_status()
    except Exception as e:
        print("Error:", e)
    return RedirectResponse("/", status_code=302)


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway(service: str, path: str, request: Request):
    if service not in SERVICE_MAP:
        raise HTTPException(status_code=404, detail="Service not found")

    url = f"{SERVICE_MAP[service]}/{path}"
    method = request.method
    headers = dict(request.headers)
    body = await request.body()

    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers, content=body)

    return response.json()
