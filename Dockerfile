FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .

# Streamable-HTTP MCP servers built on MCPServer (mcp 2.x) listen on port 8000 by default
EXPOSE 8000

CMD ["python", "server.py", "--http"]
