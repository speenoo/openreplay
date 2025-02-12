FROM ubuntu:20.04

# Install required packages
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy installation script
RUN curl -fsSL https://raw.githubusercontent.com/openreplay/openreplay/main/scripts/docker-compose/docker-install.sh -o install.sh \
    && chmod +x install.sh

# Set environment variables
ENV DOMAIN_NAME=localhost
ENV POSTGRES_STRING=""
ENV REDIS_STRING=""
ENV JWT_SECRET=""
ENV BEACON_SIZE_LIMIT=7000000
ENV ASSETS_SIZE_LIMIT=60291456
ENV DB_BATCH_SIZE_LIMIT=10000000
ENV QUEUE_MESSAGE_SIZE_LIMIT=1048576

# Expose ports
EXPOSE 8080 9000

# Set healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/healthz || exit 1

# Run installation and start services
CMD ["./install.sh"] 