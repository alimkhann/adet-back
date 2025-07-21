# Use Alpine variant for smaller footprint and pg_isready support
FROM python:3.12-alpine

# Install Postgres client (pg_isready) and build deps
RUN apk add --no-cache postgresql-client gcc musl-dev libpq

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and migration scripts
COPY . .

# Copy and enable wait‑for script
COPY scripts/wait-for-postgres.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/wait-for-postgres.sh

# Create non-root user (optional)
RUN adduser -D app && chown -R app:app /app
USER app

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/wait-for-postgres.sh", "db", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]