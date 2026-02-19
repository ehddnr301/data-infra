FROM apache/airflow:3.1.7-python3.12

# wrangler CLI 설치 (R2 업로드에 필요)
USER root
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g wrangler \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
USER airflow

# 도메인 ETL 패키지 설치
COPY domains/github/ingestion/pyproject.toml /opt/packages/gharchive-etl/pyproject.toml
COPY domains/github/ingestion/src/ /opt/packages/gharchive-etl/src/
COPY domains/discord/ingestion/pyproject.toml /opt/packages/discord-etl/pyproject.toml
COPY domains/discord/ingestion/src/ /opt/packages/discord-etl/src/

RUN pip install --no-cache-dir \
    /opt/packages/gharchive-etl \
    /opt/packages/discord-etl

# 메타DB 영속화 디렉토리 (named volume 마운트 대상)
RUN mkdir -p /opt/airflow/db

# 도메인별 데이터 디렉토리 (bind mount 시 소유권 보장)
RUN mkdir -p /opt/airflow/domains/github/ingestion/data \
             /opt/airflow/domains/discord/ingestion/data
