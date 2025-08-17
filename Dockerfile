FROM python:3.12

WORKDIR /application

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Install dev dependencies at build time if ENV is local (passed via build-arg)
ARG INSTALL_DEV_ENV=production
COPY requirements-dev.txt requirements-dev.txt
RUN if [ "$INSTALL_DEV_ENV" = "local" ] && [ -f requirements-dev.txt ]; then \
      echo "[docker] ENV=local detected at build. Installing dev dependencies" && \
      pip install -r requirements-dev.txt; \
    else \
      echo "[docker] ENV=$INSTALL_DEV_ENV. Skipping dev dependencies at build"; \
    fi

COPY . .

