FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd --create-home --uid 10001 vectorledger
WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY demo ./demo
RUN pip install .

USER vectorledger
EXPOSE 8080
ENTRYPOINT ["vectorledger"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8080"]
