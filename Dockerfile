FROM golang:1.21-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git gcc g++ make libc-dev bash librdkafka-dev cyrus-sasl openssl-dev pkgconfig

WORKDIR /app

# Copy and download dependencies
COPY backend/go.mod backend/go.sum ./
RUN go mod download

# Copy the source code
COPY backend/cmd ./cmd
COPY backend/pkg ./pkg
COPY backend/internal ./internal

# Build the application
RUN CGO_ENABLED=1 GOOS=linux go build -o service ./cmd/http

# Create final image
FROM alpine:latest

RUN apk add --no-cache ca-certificates librdkafka

WORKDIR /app

# Copy the binary from builder
COPY --from=builder /app/service .

# Create non-root user
RUN adduser -D openreplay
USER openreplay

# Expose necessary port
EXPOSE 8080

# Set healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/healthz || exit 1

# Run the application
CMD ["./service"] 