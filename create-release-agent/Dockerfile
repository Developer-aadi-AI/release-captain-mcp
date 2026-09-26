FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY create_release_agent ./create_release_agent
RUN pip install --no-cache-dir -e .
ENTRYPOINT ["create-release-agent"]
