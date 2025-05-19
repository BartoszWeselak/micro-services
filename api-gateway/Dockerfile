FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install fastapi uvicorn jinja2 aiofiles requests httpx python-multipart python-consul
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]


