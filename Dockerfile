FROM python:3.11-slim

WORKDIR /app

# Dependencies first, so adding a tool does not reinstall the world.
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "fastapi>=0.115" "uvicorn[standard]>=0.30" \
                                   "httpx>=0.27" "mcp>=1.2"

COPY services ./services
COPY skills ./skills
COPY seeds ./seeds
COPY mcp_server.py ./

EXPOSE 8304
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8304/health')"

CMD ["uvicorn", "mcp_server:app", "--host", "0.0.0.0", "--port", "8304"]
