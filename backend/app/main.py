from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .config import settings
from .routers import auth, users, request_types, requests, agent, export

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Nila — AI Workplace Access System",
    description="AI-driven access & shared resource request management",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(request_types.router)
app.include_router(requests.router)
app.include_router(agent.router)
app.include_router(export.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Nila API"}
