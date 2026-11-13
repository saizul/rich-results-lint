FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml README.md LICENSE NOTICE.md ./
COPY src ./src
RUN pip install . && useradd --system --uid 10001 app
USER app
WORKDIR /work
ENTRYPOINT ["rich-results-lint"]
CMD ["--help"]
