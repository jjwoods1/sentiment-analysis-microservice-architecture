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

# Create a non-root user (use existing group if GID 1000 exists, or create new group)
RUN addgroup -g 1001 appuser || addgroup appuser
RUN adduser -D -u 1001 -G appuser appuser || adduser -D -G appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 3000

# Start the application
CMD ["node", "build"]
