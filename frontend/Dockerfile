FROM node:20.10-alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Set environment variables
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1

# Set work directory
WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install pnpm
RUN npm install -g pnpm

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy application code
COPY . .

# Create non-root user
RUN addgroup nodejs \
    && adduser -S -G nodejs nextjs

# Change ownership of the node_modules directory
RUN chown -R nextjs:nodejs /app/node_modules

USER nextjs

# Expose port
EXPOSE 3000

# Health check - increased start-period for Next.js compilation
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Run the application
CMD ["pnpm", "dev"]