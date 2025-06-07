import os
import asyncpg
# 공통 데이터베이스 유틸리티에서 연결 풀 가져오기
from src.common.db_utils import get_db_pool

# API 키 관련 테이블 및 컬럼 이름 (auth_service에 특화된 설정)
API_KEY_TABLE_NAME = os.environ.get("API_KEY_TABLE_NAME", "api_keys")
API_KEY_COLUMN_NAME = os.environ.get("API_KEY_COLUMN_NAME", "key_value")
API_KEY_ACTIVE_COLUMN_NAME = os.environ.get("API_KEY_ACTIVE_COLUMN_NAME", "is_active")

# get_db_connection 함수는 공통 모듈의 get_db_pool로 대체되므로 제거됩니다.

async def validate_api_key_from_db(api_key: str) -> bool:
    """
    제공된 API 키가 데이터베이스에 존재하고 활성 상태인지 확인합니다.
    공통 연결 풀을 사용합니다.
    """
    if not api_key:
        return False

    pool = await get_db_pool() # 공통 풀 가져오기
    # conn = None # 직접 연결 관리 제거

    try:
        async with pool.acquire() as conn: # 풀에서 연결 가져오기
            # API 키가 테이블에 존재하고 'is_active' 컬럼이 true인지 확인하는 쿼리
            query = f"""
                SELECT EXISTS (
                    SELECT 1
                    FROM {API_KEY_TABLE_NAME}
                    WHERE {API_KEY_COLUMN_NAME} = $1 AND {API_KEY_ACTIVE_COLUMN_NAME} = TRUE
                );
            """
            exists = await conn.fetchval(query, api_key)
            return bool(exists)
    except asyncpg.PostgresError as e:
        print(f"Database query error during API key validation: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during API key validation: {e}")
        return False
    # finally: # 풀에서 가져온 연결은 'async with' 블록 종료 시 자동으로 반환되므로 명시적 close 불필요
    #     if conn:
    #         await conn.close() # 이 부분은 pool.release(conn) 또는 pool.acquire() 컨텍스트 매니저 사용 시 불필요
