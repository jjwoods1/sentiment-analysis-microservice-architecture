FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Create a non-root user (or use existing if GID/UID already exist)
RUN addgroup -g 1000 appuser 2>/dev/null || true
RUN adduser -D -u 1000 -G appuser appuser 2>/dev/null || adduser -D -u 1001 -G appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 3000

# Start the application
CMD ["node", "build"]
