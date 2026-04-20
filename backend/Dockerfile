FROM python:3.12-slim

WORKDIR /app

# Base system dependencies (curl required for ODBC; gnupg2 for key import)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg2 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Optional: install Microsoft ODBC Driver 18 for Azure SQL production use.
# Set INSTALL_ODBC=1 to enable (e.g. docker build --build-arg INSTALL_ODBC=1).
ARG INSTALL_ODBC=0
RUN if [ "$INSTALL_ODBC" = "1" ]; then \
      apt-get update && \
      apt-get install -y --no-install-recommends unixodbc-dev && \
      curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg && \
      echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list && \
      apt-get update && \
      ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 && \
      apt-get clean && rm -rf /var/lib/apt/lists/*; \
    fi

COPY pyproject.toml ./
COPY app ./app
# Install base + dev dependencies. When INSTALL_ODBC=1 (production), also
# install the azure extras so azure-identity and aioodbc are available for
# Entra-authenticated SQL connections.
RUN if [ "$INSTALL_ODBC" = "1" ]; then \
      pip install --no-cache-dir ".[dev,azure]"; \
    else \
      pip install --no-cache-dir ".[dev]"; \
    fi

COPY . .

# Create non-root user and set ownership
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
