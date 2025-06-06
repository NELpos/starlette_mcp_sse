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

# Create SSE transport
sse = SseServerTransport("/messages/")

# Retrieve the server's expected auth key from environment variable
# IMPORTANT: Set this environment variable in your deployment environment.
# For local development, you can set it in your shell, e.g., export MCP_SERVER_AUTH_KEY='your_secret_key'
SERVER_AUTH_KEY = os.environ.get("MCP_SERVER_AUTH_KEY")

def handle_sse_factory(server: FastMCP):
    async def handle_sse(request):
        if not SERVER_AUTH_KEY:
            # This case means the server is not configured for auth, which is a security risk.
            # Log this situation and potentially deny all requests, or allow if in a dev mode.
            print("CRITICAL: MCP_SERVER_AUTH_KEY is not set. SSE endpoints are insecure.")
            # For now, let's deny the connection if the server key isn't set, to be safe.
            return PlainTextResponse("Server configuration error: Auth key not set.", status_code=500)

        client_auth_key = request.headers.get("X-Auth-Key")

        if not client_auth_key:
            return PlainTextResponse("Unauthorized: Missing X-Auth-Key header", status_code=401)

        if client_auth_key != SERVER_AUTH_KEY:
            return PlainTextResponse("Unauthorized: Invalid X-Auth-Key", status_code=401)

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
