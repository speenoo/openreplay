FROM golang:1.21-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git gcc g++ make libc-dev bash librdkafka-dev cyrus-sasl openssl-dev pkgconfig

WORKDIR /build

# Clone OpenReplay repository
RUN git clone https://github.com/openreplay/openreplay.git && \
    cd openreplay && \
    git checkout v1.21.0

# Build the backend
WORKDIR /build/openreplay/backend
RUN go mod download && \
    CGO_ENABLED=1 GOOS=linux go build -o http ./cmd/http

# Final stage
FROM alpine:latest

# Install runtime dependencies
RUN apk add --no-cache ca-certificates librdkafka wget

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /build/openreplay/backend/http .

# Create startup script
RUN echo '#!/bin/sh\n\
echo "Starting OpenReplay HTTP service..."\n\
\n\
# Start the service\n\
./http &\n\
HTTP_PID=$!\n\
\n\
# Wait for service to start\n\
echo "Waiting for service to start..."\n\
sleep 10\n\
\n\
# Monitor the service\n\
while true; do\n\
  if kill -0 $HTTP_PID 2>/dev/null; then\n\
    if wget -q --spider http://localhost:8080/healthz; then\n\
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
    CMD wget -q --spider http://localhost:8080/healthz || exit 1

# Run the startup script
CMD ["./start.sh"] 