FROM apache/airflow:3.1.7-python3.12

# wrangler CLI 설치 (R2 업로드에 필요)
USER root
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g wrangler \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
USER airflow

# gharchive-etl 패키지 설치
COPY --chown=airflow:root pyproject.toml /opt/gharchive-etl/pyproject.toml
COPY --chown=airflow:root src/ /opt/gharchive-etl/src/

RUN pip install --no-cache-dir /opt/gharchive-etl

# 메타DB 영속화 디렉토리 (named volume 마운트 대상)
RUN mkdir -p /opt/airflow/db

# config.yaml, dags/, data/ 는 런타임에 볼륨 마운트로 주입
