from fastapi import FastAPI

from app.auth.router import router as auth_router


app = FastAPI(
    title="E-Commerce API",
    description="Multi-tenant e-commerce SaaS platform",
    version="1.0.0",
)


app.include_router(auth_router)


@app.get("/health")
async def health():
    return {
        "success": True,
        "message": "E-Commerce API is healthy",
        "data": {
            "status": "ok",
        },
    }