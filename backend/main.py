# main.py
from fastapi import FastAPI
from database import Base, engine
from routes import users
from fastapi.middleware.cors import CORSMiddleware

# Create all database tables
Base.metadata.create_all(bind=engine)

# Initialize app
app = FastAPI(title="Career Guidance API")
# Allow frontend JS to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include routes
app.include_router(users.router, prefix="/user", tags=["Users"])
