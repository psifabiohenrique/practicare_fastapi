from fastapi import FastAPI

app = FastAPI(title="Practicare FastAPI")


@app.get("/")
def read_root():
    return {"Hello": "World"}
