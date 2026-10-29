# Imagem da API do Nexus-AI (agente + RAG + chat web).
# Construída para linux/arm64 (VM Ampere A1 da OCI) no GitHub Actions.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    HF_HOME=/opt/huggingface

# OCR de PDFs escaneados (pytesseract + pdf2image).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-por poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

WORKDIR /app

# Dependências antes do código, para aproveitar o cache de camadas.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --extra oci

# Modelos de embeddings e reranqueamento já ficam na imagem: o container não
# depende do Hugging Face para subir e a primeira pergunta não espera download.
RUN python -c "from sentence_transformers import CrossEncoder, SentenceTransformer; \
SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'); \
CrossEncoder('cross-encoder/mmarco-mMiniLMv2-L12-H384-v1')"

# O código roda a partir de src/ (não instalado), porque contatos e curadoria
# localizam data/ relativo à raiz do projeto (/app).
COPY src ./src

# data/ (documentos, índice ChromaDB e monitoramento) fica em um volume.
RUN useradd --uid 1000 --create-home nexus \
    && mkdir -p /app/data/documents \
    && chown -R nexus /app/data
USER nexus

ENV HF_HUB_OFFLINE=1 \
    NEXUS_DOCUMENTS_DIR=/app/data/documents

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# Um único worker: os modelos ficam carregados em memória e a thread de
# sincronização usa o mesmo índice que responde as perguntas.
CMD ["uvicorn", "nexus_ai.api:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
