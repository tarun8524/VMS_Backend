from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.mongodb import connect_db, close_db
from app.db.qdrant import ensure_collection
from app.api.v1 import auth, employees, visitors, visits, locations
from app.services import location_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    ensure_collection()
    await location_service.seed_locations()
    yield
    await close_db()


app = FastAPI(
    title="Visitor Management System API",
    version="2.1.0",
    description="Face-recognition powered VMS with MongoDB + Qdrant + Email notifications",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router,       prefix="/api/v1/auth",       tags=["Auth"])
app.include_router(employees.router,  prefix="/api/v1/employees",  tags=["Employees"])
app.include_router(visitors.router,   prefix="/api/v1/visitors",   tags=["Visitors"])
app.include_router(visits.router,     prefix="/api/v1/visits",     tags=["Visits"])
app.include_router(locations.router,  prefix="/api/v1/locations",  tags=["Locations"])


@app.get("/api/v1/health", tags=["Health"])
async def health():
    return {"status": "ok", "version": "2.1.0"}
