# syntax=docker/dockerfile:1

# 1단계: Builder
FROM python:3.13-slim AS builder

WORKDIR /app

# pyproject.toml, uv.lock 복사 및 의존성 설치
COPY pyproject.toml uv.lock ./
RUN pip install --upgrade pip && \
    pip install --no-cache-dir 'uv>=0.1.0' && \
    uv pip install --system --requirement uv.lock

# 소스 코드 복사
COPY src ./src

# 2단계: Runner
FROM python:3.13-slim AS runner

WORKDIR /app

# 환경변수 설정 (필요시)
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 빌더에서 site-packages와 소스만 복사
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /app/src ./src

EXPOSE 8000

CMD ["python", "-m", "src.server"] 