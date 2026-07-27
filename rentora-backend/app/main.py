import os
import warnings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import auth, owner, tenant, dues, complaints, messages, bot, community, admin, config

app = FastAPI(
    title="Rentora API",
    description="AI-powered multi-city PG and hostel management platform",
    version="0.1.0",
)

# Only the frontend URLs listed in ALLOWED_ORIGINS (.env) can call this
# API with cookies/auth headers attached - "*" would let ANY website
# make authenticated requests on a logged-in user's behalf, which is not
# safe once this is handling real accounts and payments.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A default/guessable JWT secret means anyone can forge a valid login
# token for any account. This won't stop the app from running (so local
# dev still works out of the box), but it loudly warns so it's never
# accidentally left this way when actually deployed.
if settings.jwt_secret == "change-this-secret-key":
    warnings.warn(
        "JWT_SECRET is still the default placeholder value! Set a real, "
        "random secret in .env before deploying anywhere real users can "
        "reach this API.",
        stacklevel=1,
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