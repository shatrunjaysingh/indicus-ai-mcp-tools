# The Demo Store as a container, for a public demo address (demo.indicus-ai.com).
#
#   docker compose up -d --build demo-store        # from the repo root
#
# Only the sample app goes in: its server (app.py) and page (index.html). The
# keys come from the environment (docker-compose.yml → .env), never the image.
FROM python:3.11-slim

WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "fastapi>=0.115" "uvicorn[standard]>=0.30" "httpx>=0.27"

COPY examples/connect_sample_app/app.py examples/connect_sample_app/index.html ./

ENV HOST=0.0.0.0 PORT=8090
EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8090/api/webhooks')"

CMD ["python", "app.py"]
