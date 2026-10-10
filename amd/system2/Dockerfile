FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SYSTEM2_HOST=0.0.0.0 SYSTEM2_PORT=8083
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --no-create-home analyst
COPY analyst ./analyst
COPY scripts ./scripts
USER 10001:10001
EXPOSE 8083
HEALTHCHECK --interval=5s --timeout=3s --start-period=5s --retries=12 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8083/health', timeout=2).read()"
CMD ["python", "scripts/serve.py"]
