# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import clips, template
import os

app = FastAPI()

# Mount the jobs directory to serve rendered videos
jobs_dir = os.path.join(os.getcwd(), "jobs")
os.makedirs(jobs_dir, exist_ok=True)
app.mount("/jobs", StaticFiles(directory=jobs_dir), name="jobs")

app.include_router(clips.router)
app.include_router(template.router)