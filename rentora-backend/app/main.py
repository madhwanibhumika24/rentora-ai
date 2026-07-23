from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, owner

app = FastAPI(
    title="Rentora API",
    description="AI-powered multi-city PG and hostel management platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(owner.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "rentora-api"}