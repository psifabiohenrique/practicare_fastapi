import asyncio
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.exceptions import (
    ConflictError,
    DomainError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from routers import (
    auth_controller,
    patients_with_treatment_controller,
    treatment_record_controller,
    treatment_report_controller,
    users_controller,
)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI(title="Practicare FastAPI")


@app.exception_handler(NotFoundError)
async def not_found_exception_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": exc.message})


@app.exception_handler(ForbiddenError)
async def forbidden_exception_handler(request: Request, exc: ForbiddenError):
    return JSONResponse(status_code=403, content={"detail": exc.message})


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(status_code=400, content={"detail": exc.message})


@app.exception_handler(ConflictError)
async def conflict_exception_handler(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": exc.message})


@app.exception_handler(UnauthorizedError)
async def unauthorized_exception_handler(
    request: Request, exc: UnauthorizedError
):
    return JSONResponse(status_code=401, content={"detail": exc.message})


@app.exception_handler(DomainError)
async def domain_exception_handler(request: Request, exc: DomainError):
    return JSONResponse(status_code=500, content={"detail": exc.message})


origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:5173",
]

app.include_router(auth_controller.router)
app.include_router(users_controller.router)
app.include_router(patients_with_treatment_controller.router)
app.include_router(treatment_record_controller.router)
app.include_router(treatment_report_controller.router)

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
