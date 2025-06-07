import os
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, HTMLResponse, PlainTextResponse
from datetime import datetime
from mcp.server.sse import SseServerTransport
from services.weather import weather_mcp
from services.virustotal import virustotal_mcp
from services.jira import jira_mcp
from services.wiki import wiki_mcp
from services.pg_query import pg_query_mcp
from mcp.server.fastmcp import FastMCP
# auth_service.py에서 API 키 유효성 검사 함수를 가져옵니다 (추후 생성 예정).
from services.auth_service import validate_api_key_from_db # 추가된 import

# Create SSE transport
sse = SseServerTransport("/messages/")

# SERVER_AUTH_KEY 환경 변수 관련 로직은 데이터베이스 조회로 대체되므로 제거합니다.
# SERVER_AUTH_KEY = os.environ.get("MCP_SERVER_AUTH_KEY") 

def handle_sse_factory(server: FastMCP):
    async def handle_sse(request):
        # 기존 SERVER_AUTH_KEY 설정 여부 확인 로직 제거
        # if not SERVER_AUTH_KEY:
        #     print("CRITICAL: MCP_SERVER_AUTH_KEY is not set. SSE endpoints are insecure.")
        #     return PlainTextResponse("Server configuration error: Auth key not set.", status_code=500)

        client_auth_key = request.headers.get("X-Auth-Key")

        if not client_auth_key:
            return PlainTextResponse("Unauthorized: Missing X-Auth-Key header", status_code=401)

        # 데이터베이스를 통해 API 키 유효성 검사
        try:
            is_valid = await validate_api_key_from_db(client_auth_key)
            if not is_valid:
                return PlainTextResponse("Unauthorized: Invalid X-Auth-Key", status_code=401)
        except Exception as e:
            # 데이터베이스 연결 오류 또는 기타 예외 처리
            print(f"API key validation error: {e}")
            return PlainTextResponse("Server error during authentication.", status_code=500)


        # If authentication is successful, proceed with SSE connection
        async with sse.connect_sse(request.scope, request.receive, request._send) as (
            read_stream,
            write_stream,
        ):
            await server._mcp_server.run(
                read_stream, write_stream, server._mcp_server.create_initialization_options()
            )

    return handle_sse

# Standard web route handler functions
async def homepage(request):
    return HTMLResponse(
        "<h1>Starlette MCP SSE</h1><p>Welcome to the SSE demo with MCP integration.</p>"
    )

async def about(request):
    return PlainTextResponse(
        "About Starlette MCP SSE: A demonstration of Server-Sent Events with Model Context Protocol integration."
    )

async def status(request):
    status_info = {
        "status": "running",
        "server": "Starlette MCP SSE",
        "version": "0.1.0",
        "timestamp": datetime.now().isoformat(),
    }
    return JSONResponse(status_info)

async def docs(request):
    return PlainTextResponse(
        "API Documentation:\n"
        "- GET /sse: Server-Sent Events endpoint (Requires X-Auth-Key header)\n"
        "- POST /messages: Send messages to be broadcasted\n"
        "- GET /status: Server status information"
    )

routes = [
    Route("/", endpoint=homepage),
    Route("/about", endpoint=about),
    Route("/status", endpoint=status),
    Route("/docs", endpoint=docs),
    Mount("/messages/", app=sse.handle_post_message),

    # MCP related routes (now with authentication)
    Route("/weather/sse", endpoint=handle_sse_factory(weather_mcp)),
    Route("/virustotal/sse", endpoint=handle_sse_factory(virustotal_mcp)),
    Route("/jira/sse", endpoint=handle_sse_factory(jira_mcp)),
    Route("/wiki/sse", endpoint=handle_sse_factory(wiki_mcp)),
    Route("/pg_query/sse", endpoint=handle_sse_factory(pg_query_mcp)),
]
