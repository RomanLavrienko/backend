from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn
from presentation.routes import router as html_router
from presentation.api_routes import router as api_router
from infrastructure.repositiry.base_repository import engine

app = FastAPI()

app.mount("/assets", StaticFiles(directory="assets"), name="assets")

app.include_router(html_router)
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)
    print("MariaDB connection established!")

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)