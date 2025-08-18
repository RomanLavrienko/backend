from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn
from presentation.routes import router as html_router
from presentation.api_routes import router as api_router
from infrastructure.repositiry.base_repository import engine
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
import logging

app = FastAPI()

app.mount("/assets", StaticFiles(directory="assets"), name="assets")

app.include_router(html_router)
app.include_router(api_router)

@app.on_event("startup")
async def startup_event():
    async with engine.begin() as conn:
        await conn.run_sync(lambda _: None)
    print("MariaDB connection established!")

@app.exception_handler(Exception)
async def universal_exception_handler(request, exc):
    logging.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"},
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"message": "Validation error", "details": exc.errors()},
    )

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)