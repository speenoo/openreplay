#!/bin/bash

# Create necessary directories
mkdir -p data

# Pull the official installation script
curl -fsSL https://raw.githubusercontent.com/openreplay/openreplay/main/scripts/docker-compose/docker-install.sh -o docker-install.sh

# Make it executable
chmod +x docker-install.sh

# Run the installation with environment variables
export DOMAIN_NAME=localhost
export POSTGRES_STRING="${DATABASE_URL}"
export REDIS_STRING="${REDIS_STRING}"
export JWT_SECRET="${JWT_SECRET}"

# Run the installation
./docker-install.sh 