import logging
import os



from fastapi import FastAPI, Session

from app.routers.serve_audio import router as audio_router



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI()
app.include(audio_router)


@app.get("/")
def main():
    return {"Hello": "World"}
