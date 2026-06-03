FROM mirror2.chabokan.net/python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t /deps

FROM mirror2.chabokan.net/python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV GATEWAY_PORT=8081
ENV GATEWAY_HOST=0.0.0.0
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages
COPY config.py lm_client.py rag.py pmo_service.py document_loader.py manifest.py documents_service.py main.py ./
EXPOSE 8081
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8081/health')" || exit 1
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]
