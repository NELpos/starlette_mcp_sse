# src/common/db_utils.py
import os
import asyncpg
from typing import Optional

# --- Database Configuration (Common) ---
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "") # 기본 비밀번호는 비워두거나 적절한 기본값 사용
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "mydatabase")

DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Global connection pool
_db_pool: Optional[asyncpg.Pool] = None

async def get_db_pool() -> asyncpg.Pool:
    """
    Initializes and returns the global database connection pool.
    If the pool doesn't exist, it creates one.
    """
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = await asyncpg.create_pool(
                dsn=DB_URL,
                min_size=1,  # 최소 연결 수
                max_size=10  # 최대 연결 수
            )
            print(f"Successfully initialized database connection pool for: {DB_NAME} on {DB_HOST}:{DB_PORT}")
        except Exception as e:
            print(f"Error creating database connection pool: {e}")
            # 애플리케이션 시작 시 풀 생성이 중요하므로, 실패 시 예외를 다시 발생시켜 문제를 인지하도록 함
            raise
    return _db_pool

async def close_db_pool():
    """Closes the global database connection pool if it exists."""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        print("Database connection pool closed.")

# 애플리케이션 시작/종료 시 풀을 초기화하고 닫는 로직은
# main 애플리케이션 파일(예: main.py 또는 app.py)의 lifespan 이벤트 핸들러에서 호출하는 것이 좋습니다.
# 예시:
# from starlette.applications import Starlette
# from src.common.db_utils import get_db_pool, close_db_pool
#
# async def lifespan(app):
#     await get_db_pool() # 애플리케이션 시작 시 풀 초기화
#     yield
#     await close_db_pool() # 애플리케이션 종료 시 풀 닫기
#
# app = Starlette(lifespan=lifespan)
