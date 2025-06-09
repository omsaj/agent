from fastapi import FastAPI
from server.api import router

app = FastAPI()
app.include_router(router)

@app.get('/health')
async def health() -> dict[str, str]:
    return {"status": "ok"}
