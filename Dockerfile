FROM python:3.12

WORKDIR /application

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

# Use a readable entrypoint script:
# - Installs dev dependencies only when ENVIRONMENT=local
# - Idempotent via .dev_deps_installed marker
RUN chmod +x docker/entrypoint.sh || true
ENTRYPOINT ["sh", "docker/entrypoint.sh"]
