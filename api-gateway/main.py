from fastapi import FastAPI, Request, HTTPException, Form
import httpx
import os
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from consul import Consul
import logging
from typing import Optional
from typing import Union

app = FastAPI()

CONSUL_HOST = os.getenv("CONSUL_HOST", "localhost")  # lub "localhost", zależnie od środowiska
consul_client = Consul(host=CONSUL_HOST)

templates = Jinja2Templates(directory="templates")

# Dynamiczne odkrywanie adresu usługi z Consul
def discover_service(service_name: str) -> str | None:
    try:
        services = consul_client.agent.services()
        for service in services.values():
            if service["Service"] == service_name:
                address = service["Address"]
                port = service["Port"]
                return f"http://{address}:{port}"
    except Exception as e:
        logging.error(f"Error discovering service '{service_name}': {e}")
    return None

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    try:
        async with httpx.AsyncClient() as client:
            task_url = discover_service("task-service")
            project_url = discover_service("project-service")
            if not task_url or not project_url:
                raise Exception("One or more services unavailable")

            task_response = await client.get(f"{task_url}/tasks")
            project_response = await client.get(f"{project_url}/projects")
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
async def add_task(title: str = Form(...), description: str = Form(""),project_id: Union[int, None, str] = Form(None)):
    if project_id == "":
        project_id = None
    else:
        project_id = int(project_id)

    task_data = {
        "title": title,
        "description": description,
        "project_id": project_id,
        "is_done": False
    }
    try:
        task_url = discover_service("task-service")
        if not task_url:
            raise Exception("Task service unavailable")

        async with httpx.AsyncClient() as client:
            await client.post(f"{task_url}/tasks", json=task_data)
    except Exception as e:
        print("Error:", e)
    return RedirectResponse("/", status_code=302)

@app.post("/add-project", response_class=RedirectResponse)
async def add_project(name: str = Form(...), description: str = Form("")):
    project_data = {
        "name": name,
        "description": description,
    }
    try:
        project_url = discover_service("project-service")
        if not project_url:
            raise Exception("Project service unavailable")

        async with httpx.AsyncClient() as client:
            await client.post(f"{project_url}/projects", json=project_data)
    except Exception as e:
        print("Error:", e)
    return RedirectResponse("/", status_code=302)

@app.post("/delete-task/{task_id}", response_class=RedirectResponse)
async def delete_task(task_id: int):
    try:
        task_url = discover_service("task-service")
        if not task_url:
            raise Exception("Task service unavailable")

        async with httpx.AsyncClient() as client:
            await client.delete(f"{task_url}/tasks/{task_id}")
    except Exception as e:
        print("Delete task error:", e)
    return RedirectResponse("/", status_code=302)
#
# @app.post("/delete-project/{project_id}", response_class=RedirectResponse)
# async def delete_project(project_id: int):
#     try:
#         project_url = discover_service("project-service")
#         if not project_url:
#             raise Exception("Project service unavailable")
#
#         async with httpx.AsyncClient() as client:
#             await client.delete(f"{project_url}/projects/{project_id}")
#     except Exception as e:
#         print(f"Delete project error: {e}")
#         raise HTTPException(status_code=400, detail=str(e))
#     return RedirectResponse("/", status_code=302)
from fastapi import Query

@app.post("/delete-project/{project_id}", response_class=RedirectResponse)
async def delete_project(project_id: int, with_tasks: bool = Form(False)):
    try:
        project_url = discover_service("project-service")
        if not project_url:
            raise Exception("Project service unavailable")

        async with httpx.AsyncClient() as client:
            endpoint = (
                f"{project_url}/projects/{project_id}/with-tasks"
                if with_tasks else
                f"{project_url}/projects/{project_id}"
            )
            await client.delete(endpoint)
    except Exception as e:
        print(f"Delete project error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse("/", status_code=302)
@app.get("/edit-task/{task_id}", response_class=HTMLResponse)
async def edit_task_form(request: Request, task_id: int):
    try:
        task_url = discover_service("task-service")
        project_url = discover_service("project-service")
        if not task_url or not project_url:
            raise Exception("Required services unavailable")

        async with httpx.AsyncClient() as client:
            task_res = await client.get(f"{task_url}/tasks/{task_id}")
            projects_res = await client.get(f"{project_url}/projects")
            task = task_res.json()
            projects = projects_res.json()
    except Exception as e:
        return templates.TemplateResponse("error.html", {"request": request, "error": str(e)})

    return templates.TemplateResponse("edit_task.html", {"request": request, "task": task, "projects": projects})

@app.post("/edit-task/{task_id}", response_class=RedirectResponse)
async def edit_task(task_id: int, title: str = Form(...), description: str = Form(""),project_id: Union[int, None, str] = Form(None)
, is_done: bool = Form(False)):
    if project_id == "":
        project_id = None
    else:
        project_id = int(project_id)

    task_data = {
        "title": title,
        "description": description,
        "project_id": project_id,
        "is_done": is_done
    }
    try:
        task_url = discover_service("task-service")
        if not task_url:
            raise Exception("Task service unavailable")

        async with httpx.AsyncClient() as client:
            await client.put(f"{task_url}/tasks/{task_id}", json=task_data)
    except Exception as e:
        print("Edit task error:", e)
    return RedirectResponse("/", status_code=302)

@app.get("/edit-project/{project_id}", response_class=HTMLResponse)
async def edit_project_form(request: Request, project_id: int):
    try:
        project_url = discover_service("project-service")
        if not project_url:
            raise Exception("Project service unavailable")

        async with httpx.AsyncClient() as client:
            res = await client.get(f"{project_url}/projects/{project_id}")
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
        project_url = discover_service("project-service")
        if not project_url:
            raise Exception("Project service unavailable")

        async with httpx.AsyncClient() as client:
            await client.put(f"{project_url}/projects/{project_id}", json=project_data)
    except Exception as e:
        print("Edit project error:", e)
    return RedirectResponse("/", status_code=302)

@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway(service: str, path: str, request: Request):
    service_lookup = {
        "tasks": "task-service",
        "projects": "project-service"
    }

    if service not in service_lookup:
        raise HTTPException(status_code=404, detail="Service not found")

    service_url = discover_service(service_lookup[service])
    if not service_url:
        raise HTTPException(status_code=503, detail="Service unavailable")

    url = f"{service_url}/{path}"
    method = request.method
    headers = dict(request.headers)
    body = await request.body()

    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers, content=body)

    return response.json()

@app.get("/health")
def health_check():
    return {"status": "UP"}