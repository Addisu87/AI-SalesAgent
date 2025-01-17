import os
import uuid

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from fastapi import HTTPException

# Retrieve environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")

# Initialize ElevenLabs client
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


def text_to_speech(text: str) -> bytes:
    """
    Converts text to speech using the ElevenLabs API and returns the audio content as bytes.

    Args:
        text (str): The text to be converted to speech.

    Returns:
        bytes: The audio content in binary format.

    Raises:
        HTTPException: If the API call fails.
    """
    try:
        response = client.text_to_speech.convert(
            voice_id=VOICE_ID,
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_turbo_v2_5",
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
            ),
        )

        if response.status_code == 200:
            return response.content
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to generate speech: {response.text}",
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


def save_audio_file(audio_data: bytes) -> str:
    """
    Saves audio data to a file and returns the file path.

    Args:
        audio_data (bytes): The binary audio data to be saved.

    Returns:
        str: The path to the saved audio file.
    """
    try:
        # Ensure the directory exists
        output_dir = "audio_files"
        os.makedirs(output_dir, exist_ok=True)

        # Generate a unique file name
        file_name = f"{uuid.uuid4()}.mp3"
        file_path = os.path.join(output_dir, file_name)

        # Write the audio data to the file
        with open(file_path, "wb") as audio_file:
            audio_file.write(audio_data)

        print(f"{file_path}: A new audio file was saved successfully!")

        return file_path
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save audio file: {str(e)}"
        )
