from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import check_db_connection
from app.routers import models as model_routes
from app.routers import predictions as prediction_routes

app = FastAPI(title="BOATRACE=LOVE API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(model_routes.router)
app.include_router(prediction_routes.router)


# 戻り値の型 `-> dict[str, str]` を追加
@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "boatrace-love-api"}


@app.get("/db/health")
def db_health_check() -> dict[str, str]:
    if check_db_connection():
        return {"status": "ok", "database": "connected"}

    raise HTTPException(status_code=503, detail="Database connection failed")


@app.get("/version")
def get_version() -> dict[str, str]:
    return {"version": "0.1.0"}
