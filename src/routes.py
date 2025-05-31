from starlette.routing import Route, Mount
from starlette.responses import JSONResponse, HTMLResponse, PlainTextResponse
from datetime import datetime
from mcp.server.sse import SseServerTransport
from weather import weather_mcp

# Create SSE transport
sse = SseServerTransport("/messages/")

# MCP SSE handler function
async def handle_sse(request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (
        read_stream,
        write_stream,
    ):
        await weather_mcp._mcp_server.run(
            read_stream, write_stream, weather_mcp._mcp_server.create_initialization_options()
        )

# def handle_sse_factory(server:FastMCP):
#     async def handle_sse(request):
#         async with sse.connect_sse(request.scope, request.receive, request._send) as (
#             read_stream,
#             write_stream,
#         ):
#             await server._mcp_server.run(
#                 read_stream, write_stream, server._mcp_server.create_initialization_options()
#             )
    
#     return handle_sse
# #...
# # All routes list, including standard web routes and MCP routes
# routes = [
#     Route("/", endpoint=homepage),
#     Route("/about", endpoint=about),
#     Route("/status", endpoint=status),
#     Route("/docs", endpoint=docs),
#     # MCP related routes
#     Route("/math/sse", endpoint=handle_sse_factory(mcp)),
#     Route("/test/sse", endpoint=handle_sse_factory(test_mcp)),

#     Mount("/messages/", app=sse.handle_post_message),
# ]


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


# All routes list, including standard web routes and MCP routes
routes = [
    Route("/", endpoint=homepage),
    Route("/about", endpoint=about),
    Route("/status", endpoint=status),
    Route("/docs", endpoint=docs),
    # MCP related routes
    Route("/sse", endpoint=handle_sse),
    Mount("/messages/", app=sse.handle_post_message),
]
