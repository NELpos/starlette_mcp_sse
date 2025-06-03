from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, HTMLResponse, PlainTextResponse
from datetime import datetime
from mcp.server.sse import SseServerTransport
from servers.weather import weather_mcp
from servers.virustotal import virustotal_mcp   
from mcp.server.fastmcp import FastMCP

# Create SSE transport
sse = SseServerTransport("/messages/")

def handle_sse_factory(server:FastMCP):
    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as (
            read_stream,
            write_stream,
        ):
            await server._mcp_server.run(
                read_stream, write_stream, server._mcp_server.create_initialization_options()
            )
    
    return handle_sse




# async def handle_sse(request):
#     async with sse.connect_sse(request.scope, request.receive, request._send) as (
#         read_stream,
#         write_stream,
#     ):
#         await weather_mcp._mcp_server.run(
#             read_stream, write_stream, weather_mcp._mcp_server.create_initialization_options()
#         )





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
        "- GET /sse: Server-Sent Events endpoint\n"
        "- POST /messages: Send messages to be broadcasted\n"
        "- GET /status: Server status information"
    )

routes = [
    Route("/", endpoint=homepage),
    Route("/about", endpoint=about),
    Route("/status", endpoint=status),
    Route("/docs", endpoint=docs),
    Mount("/messages/", app=sse.handle_post_message),

    # MCP related routes
    Route("/weather/sse", endpoint=handle_sse_factory(weather_mcp)),
    Route("/virustotal/sse", endpoint=handle_sse_factory(virustotal_mcp)),
]
