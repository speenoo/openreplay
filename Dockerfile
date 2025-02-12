FROM golang:1.23-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git gcc g++ make libc-dev bash librdkafka-dev cyrus-sasl openssl-dev pkgconfig

WORKDIR /build

# Clone OpenReplay repository and modify go.mod
RUN git clone https://github.com/openreplay/openreplay.git && \
    cd openreplay && \
    git checkout v1.21.0 && \
    cd backend && \
    sed -i 's/go 1.23/go 1.22/' go.mod

# Build the backend
WORKDIR /build/openreplay/backend
RUN go mod download && \
    CGO_ENABLED=1 GOOS=linux go build -o http ./cmd/http

# Final stage
FROM alpine:latest

# Install runtime dependencies
RUN apk add --no-cache ca-certificates librdkafka wget curl

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /build/openreplay/backend/http .

# Create startup script
RUN echo '#!/bin/sh\n\
echo "Starting OpenReplay HTTP service..."\n\
\n\
# Set host to 0.0.0.0\n\
export HOST="0.0.0.0"\n\
\n\
# Start the service\n\
./http &\n\
HTTP_PID=$!\n\
\n\
# Wait for service to start\n\
echo "Waiting for service to start..."\n\
sleep 15\n\
\n\
# Monitor the service\n\
while true; do\n\
  if kill -0 $HTTP_PID 2>/dev/null; then\n\
    if curl -s -f http://0.0.0.0:8080/healthz >/dev/null 2>&1; then\n\
      echo "Service is healthy"\n\
    else\n\
      echo "Service is running but not healthy"\n\
    fi\n\
  else\n\
    echo "Service has stopped, exiting..."\n\
    exit 1\n\
  fi\n\
  sleep 5\n\
done' > start.sh && chmod +x start.sh

# Set environment variables
ENV HOST=0.0.0.0
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
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://0.0.0.0:8080/healthz || exit 1

# Run the startup script
CMD ["./start.sh"]