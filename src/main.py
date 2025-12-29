from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, users

app = FastAPI(title="Practicare FastAPI")

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:5173",
]

app.include_router(auth.router)
app.include_router(users.router)

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
