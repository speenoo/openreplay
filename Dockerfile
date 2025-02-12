FROM ubuntu:20.04

# Prevent interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install required packages
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    docker.io \
    docker-compose \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy installation script
RUN curl -fsSL https://raw.githubusercontent.com/openreplay/openreplay/main/scripts/docker-compose/docker-install.sh -o install.sh \
    && chmod +x install.sh

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Starting OpenReplay services..."\n\
./install.sh\n\
echo "Installation complete, starting health check..."\n\
while true; do\n\
  if wget --no-verbose --tries=1 --spider http://localhost:8080/healthz; then\n\
    echo "Service is healthy"\n\
    sleep 30\n\
  else\n\
    echo "Service is not healthy, checking logs..."\n\
    sleep 5\n\
  fi\n\
done' > start.sh && chmod +x start.sh

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

# Set healthcheck with longer interval and start period
HEALTHCHECK --interval=30s --timeout=30s --start-period=120s --retries=5 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/healthz || exit 1

# Run the startup script
CMD ["./start.sh"] 