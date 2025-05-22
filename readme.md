# YourVibes AI Service

## Overview
The YourVibes AI Service is a Python-based service designed to provide AI-powered content moderation for the YourVibes ecosystem. It detects and censors sensitive text and media content (e.g., in posts and comments) to ensure a safe user experience on the platform.

This service integrates with the main Golang backend and uses machine learning models to analyze content. It leverages **PyTorch** and **HuggingFace Transformers** for text and media detection.

## Role in the YourVibes Ecosystem
The AI Service is responsible for:
- **Content Moderation**: Detecting sensitive or inappropriate content in posts and comments.
- **Text Detection**: Using HuggingFace Transformers to analyze and flag text-based content.
- **Media Detection**: Processing images and other media to identify inappropriate content.

It communicates with the main Golang backend in two ways:
- **RabbitMQ (Message Queue)**: For asynchronous post censoring. Posts are sent to the AI service via RabbitMQ, processed, and results are sent back to the backend.
- **gRPC (Asynchronous)**: For real-time communication, such as comment censoring, where the backend requests immediate results from the AI service.

## Functions of the Python Server
The Python server provides the following content moderation functions:
- **Media Censoring**: Analyzes media (e.g., images, videos) to detect inappropriate content, including:
  - **Abuse**: Content that promotes harassment or bullying.
  - **NSFW**: Explicit or adult content.
  - **Political**: Sensitive political content that may incite conflict.
  - **Violence**: Content depicting or promoting violence.
  - If such content is detected, the media is flagged and blocked from being posted or displayed.
- **Text Censoring**: Analyzes text in posts and comments for inappropriate content (e.g., abusive language, NSFW terms, political extremism, or violent language).
  - If sensitive text is detected, the content is censored by replacing the inappropriate words or phrases with asterisks (`*`). For example, a comment like "This is offensive content" might be censored as "This is ******** content" if "offensive" is flagged.

## Technologies Used
- **PyTorch**: A deep learning framework used for building and running machine learning models for content moderation.
- **HuggingFace Transformers**: Provides pre-trained models for natural language processing (NLP) to detect sensitive text.
- **RabbitMQ**: Message queue for asynchronous communication with the Golang backend.
- **gRPC**: For efficient, real-time communication with the backend.

## Setup Instructions

### Prerequisites
- Python 3.10 required
- RabbitMQ (running locally or accessible via network)

### Steps

1. **Clone the Repository**
   ```bash
   git clone https://github.com/poin4003/yourvibes_ai_service.git
   cd yourvibes_ai_service
   ```

2. **Create Configuration File**
   - Create a `config` folder in the root directory.
   - Add `dev.yaml` or `prod.yaml` with the following content (fill in any private data):
     ```yaml
     server:
       port: 5000
     rabbitmq:
       url: "amqp://guest:guest@localhost:5672/"
       username: "guest"
       password: "guest"
       vhost: "/"
       connection_timeout: 10
       max_reconnect_attempts: 5
     comment_censor_grpc_conn:
       port: 50051
       host: localhost
     ```

3. **Set Up Virtual Environment**
   - Create and activate a Python virtual environment:
     ```bash
     python -m venv venv
     ```
   - Activate the virtual environment:
     - On Windows:
       ```bash
       venv\Scripts\activate
       ```
     - On macOS/Linux:
       ```bash
       source venv/bin/activate
       ```

4. **Install Dependencies**
   - Install the required Python packages listed in `requirements.txt`:
     ```bash
     pip install -r requirements.txt
     ```

5. **Run the Server**
   - For development:
     ```bash
     make dev
     ```
     - This runs the server in HTTP mode, and the service will call the Golang backend APIs for media retrieval using HTTP.
   - For production:
     ```bash
     make prod
     ```
     - This runs the server in production mode, and the service will call the Golang backend APIs for media retrieval using HTTPS.

### Notes
- Ensure RabbitMQ is running before starting the service.
- The `comment_censor_grpc_conn` settings must match the Golang backend's gRPC configuration for successful communication.
- If you encounter issues with the media API calls, verify the Golang backend's server configuration (HTTP or HTTPS) matches the mode you're using (`make dev` or `make prod`).