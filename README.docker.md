# Docker Setup for Rohdex-POC

This document explains how to build and run the Rohdex-POC application using Docker.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

## Configuration

1. Copy `.env.example` to `.env` and fill in your configuration:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file to include:
   - Your Anthropic API key or OpenAI API key
   - Email configuration (Gmail or other)
   - Model configuration

## Building and Running with Docker Compose

The easiest way to run the application is with Docker Compose:

```bash
# Build and start the container in the background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

## Building and Running with Docker

If you prefer to use Docker directly:

```bash
# Build the Docker image
docker build -t rohdex-poc .

# Run the container
docker run -p 8000:8000 --env-file .env -v $(pwd)/logs:/app/logs -v $(pwd)/context:/app/context rohdex-poc
```

## Accessing the Application

Once the container is running, you can access:

- Health Check: http://localhost:8000/api/v1/health

## Processing Emails Manually

To manually trigger email processing:

```bash
curl -X POST "http://localhost:8000/api/v1/packing-list/process-email" -H "Content-Type: application/json"
```

## Troubleshooting

If you encounter issues:

1. Check the container logs:
   ```bash
   docker-compose logs
   ```

2. Verify all required environment variables are set in the `.env` file

3. Ensure the ports are not already in use on your host machine

4. If you're using Gmail for email processing, ensure you've set up an "App Password" in your Google account settings 