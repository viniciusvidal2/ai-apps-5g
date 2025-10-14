#!/bin/bash

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h postgres -p 5432 -U gabriel; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is up - executing migrations"

# Run database migrations
echo "Running database migrations..."
cd /app && npx drizzle-kit push --config=drizzle.config.ts

# Check if migrations were successful
if [ $? -eq 0 ]; then
  echo "Database migrations completed successfully"
else
  echo "Database migrations failed"
  exit 1
fi

# Create a fixed guest user
echo "Creating fixed guest user..."
cd /app && node create-guest.js

# Start the Next.js application
echo "Starting Next.js application..."
exec pnpm dev
