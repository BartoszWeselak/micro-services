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


@app.post("/delete-task/{task_id}", response_class=RedirectResponse)
async def delete_task(task_id: int):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{SERVICE_MAP['tasks']}/tasks/{task_id}")
            response.raise_for_status()
    except Exception as e:
        print("Delete task error:", e)
    return RedirectResponse("/", status_code=302)

@app.post("/delete-project/{project_id}", response_class=RedirectResponse)
async def delete_project(project_id: int):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(f"{SERVICE_MAP['projects']}/projects/{project_id}")
            response.raise_for_status()
    except Exception as e:
        print(f"Delete project error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse("/", status_code=302)
@app.get("/edit-task/{task_id}", response_class=HTMLResponse)
async def edit_task_form(request: Request, task_id: int):
    try:
        async with httpx.AsyncClient() as client:
            task_res = await client.get(f"{SERVICE_MAP['tasks']}/tasks/{task_id}")
            projects_res = await client.get(f"{SERVICE_MAP['projects']}/projects")
            task = task_res.json()
            projects = projects_res.json()
    except Exception as e:
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)})

    return templates.TemplateResponse("edit_task.html", {"request": request, "task": task, "projects": projects})

@app.post("/edit-task/{task_id}", response_class=RedirectResponse)
async def edit_task(task_id: int, title: str = Form(...), description: str = Form(""), project_id: int = Form(...), is_done: bool = Form(False)):
    task_data = {
        "title": title,
        "description": description,
        "project_id": project_id,
        "is_done": is_done
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.put(f"{SERVICE_MAP['tasks']}/tasks/{task_id}", json=task_data)
    except Exception as e:
        print("Edit task error:", e)
    return RedirectResponse("/", status_code=302)


@app.get("/edit-project/{project_id}", response_class=HTMLResponse)
async def edit_project_form(request: Request, project_id: int):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{SERVICE_MAP['projects']}/projects/{project_id}")
            project = res.json()
    except Exception as e:
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)})

    return templates.TemplateResponse("edit_project.html", {"request": request, "project": project})

@app.post("/edit-project/{project_id}", response_class=RedirectResponse)
async def edit_project(project_id: int, name: str = Form(...), description: str = Form("")):
    project_data = {
        "name": name,
        "description": description
    }
    try:
        async with httpx.AsyncClient() as client:
            await client.put(f"{SERVICE_MAP['projects']}/projects/{project_id}", json=project_data)
    except Exception as e:
        print("Edit project error:", e)
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
