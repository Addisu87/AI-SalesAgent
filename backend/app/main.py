from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers.call_router import router as audio_router
from backend.app.helpers.tools_helpers import setup_logger

# Configure logging
logger = setup_logger("Main")

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(audio_router)


@app.get("/")
def main():
    return {"message": "AI Sales Agent is running!"}
