import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.serve_audio import router as audio_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include(audio_router)


@app.get("/")
def main():
    return {"Hello": "World"}
