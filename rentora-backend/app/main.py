import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import auth, owner, tenant, dues, complaints, messages, bot, community, admin, config

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

# Property photos get saved to this folder on disk and served back out
# at /uploads/... . We create the folder if it doesn't exist yet so the
# app doesn't crash on a fresh clone of the project.
os.makedirs("uploads/properties", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(owner.router)
app.include_router(tenant.router)
app.include_router(dues.router)
app.include_router(complaints.router)
app.include_router(messages.router)
app.include_router(bot.router)
app.include_router(community.router)
app.include_router(admin.router)
app.include_router(config.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "rentora-api"}