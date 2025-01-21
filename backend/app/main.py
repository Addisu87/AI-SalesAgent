from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.serve_audio import router as audio_router
from app.utils.tools import setup_logger

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
app.include(audio_router)


@app.get("/")
def main():
    return {"message": "AI Sales Agent is running!"}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0.", port=8000)
