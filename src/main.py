from fastapi import FastAPI

from routers import auth, users

app = FastAPI(title="Practicare FastAPI")

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/")
def read_root():
    return {"Hello": "World"}
