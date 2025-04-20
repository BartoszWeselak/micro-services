from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# === DB CONFIG ===
DATABASE_URL = "postgresql://user:password@project-db:5432/projectdb"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# === ORM MODEL ===
class ProjectORM(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)

# === Pydantic model ===
class Project(BaseModel):
    id: int
    name: str
    description: str = ""

    class Config:
        orm_mode = True

# === FASTAPI SETUP ===
app = FastAPI()

# Tworzenie tabel przy starcie
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# Dependency: sesja DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === ENDPOINTY ===

@app.get("/projects", response_model=List[Project])
def get_projects(db: Session = Depends(get_db)):
    return db.query(ProjectORM).all()

@app.post("/projects", response_model=Project)
def create_project(project: Project, db: Session = Depends(get_db)):
    db_project = ProjectORM(**project.dict())
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
    return {"message": "Project deleted"}
