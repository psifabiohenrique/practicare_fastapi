import asyncio
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import (
    auth_controller,
    patients_with_treatment_controller,
    treatment_record_controller,
    users_controller,
)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI(title="Practicare FastAPI")

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:5173",
]

app.include_router(auth_controller.router)
app.include_router(users_controller.router)
app.include_router(patients_with_treatment_controller.router)
app.include_router(treatment_record_controller.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"Hello": "World"}
