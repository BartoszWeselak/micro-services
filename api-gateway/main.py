from fastapi import FastAPI, Request, HTTPException
import httpx
import os

app = FastAPI()

SERVICE_MAP = {
    "tasks": "http://task-service:8001",
    "projects": "http://project-service:8002",
    "communication": "http://communication-service:8005",
    "report": "http://report-service:8003",
    "schedule": "http://schedule-service:8004",
}

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
