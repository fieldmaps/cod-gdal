FROM ghcr.io/osgeo/gdal:ubuntu-full-3.10.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    python3-pip python3-venv rclone \
    && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

CMD ["fastapi", "run", "app", "--port", "80"]
