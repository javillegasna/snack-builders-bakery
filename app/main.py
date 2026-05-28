from fastapi import FastAPI

app = FastAPI(title="Snack Builders Bakery API")


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    return {"status": "ok"}
