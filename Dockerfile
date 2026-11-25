FROM python:3.14.10-slim-trixie

RUN apt-get update \
    && apt-get install -y --no-install-recommends iputils-ping \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py README.md CHANGELOG.md ./
COPY docs/*.md ./docs/
COPY static ./static

RUN useradd -u 1000 -m app && mkdir -p /data && chown app /data
USER app

EXPOSE 5001
CMD ["python", "main.py"]
