from fastapi import FastAPI

app = FastAPI(title="Medix Appointments API")


@app.get("/")
def hello_world() -> dict[str, str]:
    return {"message": "Hello World"}
