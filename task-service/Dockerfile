FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install fastapi uvicorn pydantic sqlalchemy psycopg2-binary python-consul
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]