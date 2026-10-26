FROM python:3.13-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi==0.115.11 \
    "uvicorn[standard]==0.34.0" \
    httpx==0.28.1 \
    pydantic==2.10.6 \
    python-dotenv==1.0.1

# Copy proxy code into /app/apps/free_llm_proxy to match python package structure
COPY . /app/apps/free_llm_proxy/

WORKDIR /app/apps/free_llm_proxy

EXPOSE 8086

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8086"]
