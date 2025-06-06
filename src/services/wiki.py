from typing import Any, Dict, Optional
import httpx
import os
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server for Confluence Wiki
wiki_mcp = FastMCP("wiki")

# --- Configuration ---
# TODO: Replace with your Atlassian domain (e.g., "your-domain.atlassian.net")
ATLASSIAN_DOMAIN = os.environ.get("ATLASSIAN_DOMAIN", "")
# TODO: Replace with your Confluence Personal Access Token (PAT)
# It's recommended to store this as an environment variable for security.
# How to create a PAT: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/
CONFLUENCE_PAT = os.environ.get("CONFLUENCE_PAT", "")

CONFLUENCE_API_V1_BASE = f"https://{ATLASSIAN_DOMAIN}/wiki/rest/api"

async def confluence_request(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Helper function to make requests to the Confluence API (v1 only)."""
    if not ATLASSIAN_DOMAIN or not CONFLUENCE_PAT:
        return {"error": "ATLASSIAN_DOMAIN and CONFLUENCE_PAT must be configured."}

    base_url = CONFLUENCE_API_V1_BASE  # Always use V1
    url = f"{base_url}{endpoint}"

    headers = {
        "Authorization": f"Bearer {CONFLUENCE_PAT}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30.0,
            )
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            if response.status_code == 204: # No content
                return {"status": "success", "message": "Operation successful, no content returned."}
            return response.json()
        except httpx.HTTPStatusError as e:
            try:
                error_details = e.response.json()
            except Exception:
                error_details = e.response.text
            return {
                "error": f"HTTP error: {e.response.status_code} - {e.response.reason_phrase}",
                "details": error_details,
            }
        except httpx.RequestError as e:
            return {"error": f"Request error: {str(e)}"}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {str(e)}"}

@wiki_mcp.tool()
async def get_user_info() -> Dict[str, Any]:
    """GET /wiki/rest/api/user/current - Retrieves the currently authenticated user's information."""
    return await confluence_request("/user/current")

@wiki_mcp.tool()
async def search_content(cql: str) -> Dict[str, Any]:
    """GET /wiki/rest/api/content/search?cql={CQL} - Searches for content using Confluence Query Language (CQL).

    Args:
        cql: The Confluence Query Language string. E.g., 'type=page and space=MYSPACEKEY and title ~ "My Page Title"'
             Documentation: https://developer.atlassian.com/cloud/confluence/advanced-searching-using-cql/
    """
    # CQL needs to be URL encoded, but httpx params handle this automatically.
    # However, if constructing the URL manually, ensure proper encoding.
    return await confluence_request("/content/search", params={"cql": cql})

@wiki_mcp.tool()
async def get_page_content(page_id: str) -> Dict[str, Any]:
    """GET /wiki/rest/api/content/{id} - Retrieves the content of a specific page by its ID.

    Args:
        page_id: The ID of the page to retrieve.
    """
    return await confluence_request(f"/content/{page_id}")

@wiki_mcp.tool()
async def get_space_info(space_id: str) -> Dict[str, Any]:
    """GET /wiki/rest/api/space/{spaceKey} - Retrieves information about a specific space by its key (ID).

    Args:
        space_id: The key (ID) of the space to retrieve.
    """
    return await confluence_request(f"/space/{space_id}")

@wiki_mcp.tool()
async def list_spaces(limit: int = 25, cursor: Optional[str] = None) -> Dict[str, Any]:
    """GET /wiki/rest/api/space - Retrieves a list of all spaces.

    Args:
        limit: The maximum number of spaces to return (default 25, max 250).
        cursor: Cursor for pagination to retrieve the next set of results.
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return await confluence_request("/space", params=params)

@wiki_mcp.tool()
async def get_page_children(page_id: str, limit: int = 25, cursor: Optional[str] = None) -> Dict[str, Any]:
    """GET /wiki/rest/api/content/{id}/child - Retrieves the children (e.g. pages, comments) of a specific content item by ID.

    Args:
        page_id: The ID of the parent page.
        limit: The maximum number of children to return (default 25, max 250).
        cursor: Cursor for pagination to retrieve the next set of results.
    """
    params = {"limit": limit}
    if cursor:
        params["cursor"] = cursor
    return await confluence_request(f"/content/{page_id}/child", params=params)

if __name__ == "__main__":
    if not ATLASSIAN_DOMAIN or not CONFLUENCE_PAT:
        print("Error: ATLASSIAN_DOMAIN and CONFLUENCE_PAT environment variables must be set.")
        print("Please set them before running the server.")
        print("Example: export ATLASSIAN_DOMAIN=\"your-domain.atlassian.net\"")
        print("Example: export CONFLUENCE_PAT=\"your_personal_access_token\"")
    else:
        print(f"Wiki MCP server running for domain: {ATLASSIAN_DOMAIN}")
        print("Available tools:")
        for tool_name in wiki_mcp.tools:
            print(f"- {tool_name}")
        wiki_mcp.run(transport="sse")
