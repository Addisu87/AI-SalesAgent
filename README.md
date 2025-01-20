# AI-SalesAgent

It is an ai-sales agent app using fastAPI

Below is the description of each file and their purpose in the project.

- **.env_sample**: A sample environment variable file that should be copied to `.env` for configuring the application secrets and settings.
- **ai_helpers.py**: Contains helper functions for AI operations, such as interacting with machine learning models and APIs.
- **main.py**: The main fastapi python application file.
- **server-audio.py** It defines HTTP routes and the web server logic.
- **config.py**: Configuration file or setting up global variables and settings.
- **prompts.py**: Likely includes predefined prompts for different logic within this application.
- **stages.py**: Define various stages or states of a process in a standard Sales process.
- **tools.py**: Provides additional utilities functions or tools that can be used throughout the application for various tasks.
- **Dockerfile**: to build the Docker image for the application, specifying the environment, dependency and commands.
- **docker-compose.yml**: To define and run multi-container Docker applications. Specifies services, networks, volumes.

### Prerequisites

- Docker
- Docker Compose
- Create a Twillo Account - Create a phone number
- Create a free Elevenlabs Account
- Create a free Groq account and create keys
- For improved response from AI agent, use OpenAI APIs.
- Register yourself to NGROK
- Open a Terminal & run

```bash
ngrok http 5000
```

This will create a public link such as https"//a98d-82-26-133-9.ngrok-free.app

### Steps to Run

1. Clone the repository or download the files to your local machine.
2. Navigate to the project directory where `docker.compose.yml` is located.
3. Copy `.env_sample` to `.env` and modify the environment variables as per your requirements.
4. Run the following command to build and start the containers.
   ```bash
       docker-compose up --build
   ```
5. Once the containers are running, access the application via `http://localhost:5000` or another configured port.

### Stopping the Application

- To stop the application, use the following Docker Compose command:

```bash
docker-compose down
```

### Changing underlying code

- If you've changed any code in the application, please make sure to use the following command to rebuild the image and start it.

```bash
docker-compose build --no-cache
docker-compose up
```

<!-- Initialize the app -->

```bash
    uvicorn app.main:app --reload
```

```bash
    pip install -r requirements.txt
```
