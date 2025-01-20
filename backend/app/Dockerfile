# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Install any needed packages specified in the requirements.txt
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Create a directory for audio files
RUN mkdir -p /usr/src/app/audio_files

# Copy the current directory contents into the container as /usr/src/app
COPY . .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run app.main:app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]
