from typing import Any, Dict, Optional, List, Union
import httpx
import os
import base64
from urllib.parse import quote

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server for Jira
jira_mcp = FastMCP("jira")

# --- Configuration ---
# TODO: Ensure this is your Atlassian domain (e.g., "your-domain.atlassian.net")
ATLASSIAN_DOMAIN = os.environ.get("ATLASSIAN_DOMAIN", "")
# TODO: Set your Jira User Email and API Token as environment variables
# How to create an API Token: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/
JIRA_USER_EMAIL = os.environ.get("JIRA_USER_EMAIL", "")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")

JIRA_API_BASE = f"https://{ATLASSIAN_DOMAIN}/rest/api/3"

async def jira_request(
    endpoint_or_url: str,
    method: str = "GET",
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    expect_json: bool = True,
) -> Union[Dict[str, Any], bytes]:
    """Helper function to make requests to the Jira API (v3).
    Can handle both relative API endpoints and full URLs.
    """
    if not ATLASSIAN_DOMAIN or not JIRA_USER_EMAIL or not JIRA_API_TOKEN:
        return {
            "error": "ATLASSIAN_DOMAIN, JIRA_USER_EMAIL, and JIRA_API_TOKEN must be configured."
        }

    auth_string = f"{JIRA_USER_EMAIL}:{JIRA_API_TOKEN}"
    auth_header_value = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_header_value}",
    }

    if expect_json:
        headers["Accept"] = "application/json"
    else:
        headers["Accept"] = "*/*" # Generic accept for downloads
    
    if json_data is not None:
        headers["Content-Type"] = "application/json"

    if endpoint_or_url.startswith("http://") or endpoint_or_url.startswith("https://"):
        url = endpoint_or_url
    else:
        url = f"{JIRA_API_BASE}{endpoint_or_url}"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=60.0,  # Increased timeout for potential downloads
            )
            response.raise_for_status()

            if not expect_json:
                return response.content  # Return raw bytes for downloads

            # Handle JSON responses
            if response.status_code == 204:  # No content
                return {"status": "success", "message": "Operation successful, no content returned."}
            
            if response.status_code == 201 and method == "POST": # Created resource
                try:
                    return response.json()
                except Exception: # If no JSON body after 201, still indicate success
                    return {"status": "created", "message": "Resource created, no JSON body returned."}

            return response.json()  # Default for other successful JSON responses (e.g. 200 GET)

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

# --- Tool Implementations ---

@jira_mcp.tool()
async def create_issue(payload: Dict[str, Any]) -> Dict[str, Any]:
    """새로운 이슈 생성 (POST /rest/api/3/issue)"""
    return await jira_request(endpoint="/issue", method="POST", json_data=payload)

@jira_mcp.tool()
async def update_issue(issue_id_or_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """기존 이슈 업데이트 (PUT /rest/api/3/issue/{issueIdOrKey})"""
    return await jira_request(endpoint=f"/issue/{issue_id_or_key}", method="PUT", json_data=payload)

@jira_mcp.tool()
async def add_comment(issue_id_or_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """이슈에 댓글 추가 (POST /rest/api/3/issue/{issueIdOrKey}/comment)"""
    return await jira_request(endpoint=f"/issue/{issue_id_or_key}/comment", method="POST", json_data=payload)

@jira_mcp.tool()
async def get_comments(issue_id_or_key: str, start_at: Optional[int] = None, max_results: Optional[int] = None) -> Dict[str, Any]:
    """이슈의 모든 댓글 조회 (GET /rest/api/3/issue/{issueIdOrKey}/comment)"""
    params = {}
    if start_at is not None:
        params['startAt'] = start_at
    if max_results is not None:
        params['maxResults'] = max_results
    return await jira_request(endpoint=f"/issue/{issue_id_or_key}/comment", method="GET", params=params if params else None)

@jira_mcp.tool()
async def get_user_info() -> Dict[str, Any]:
    """인증된 사용자 정보 조회 (GET /rest/api/3/myself)"""
    return await jira_request(endpoint="/myself", method="GET")

@jira_mcp.tool()
async def get_issue(issue_id_or_key: str, fields: Optional[str] = None, expand: Optional[str] = None) -> Dict[str, Any]:
    """특정 이슈 상세 정보 조회 (GET /rest/api/3/issue/{issueIdOrKey})"""
    params = {}
    if fields:
        params['fields'] = fields
    if expand:
        params['expand'] = expand
    return await jira_request(endpoint=f"/issue/{issue_id_or_key}", method="GET", params=params if params else None)

@jira_mcp.tool()
async def get_issue_comment(issue_id_or_key: str, comment_id: str) -> Dict[str, Any]:
    """특정 댓글 상세 정보 조회 (GET /rest/api/3/issue/{issueIdOrKey}/comment/{id})"""
    return await jira_request(endpoint=f"/issue/{issue_id_or_key}/comment/{comment_id}", method="GET")

@jira_mcp.tool()
async def search_issues(jql_query: str, start_at: Optional[int] = None, max_results: Optional[int] = None, fields: Optional[str] = None, expand: Optional[str] = None) -> Dict[str, Any]:
    """JQL을 사용하여 이슈 검색 (GET /rest/api/3/search?jql={query})"""
    params = {"jql": jql_query}
    if start_at is not None:
        params['startAt'] = start_at
    if max_results is not None:
        params['maxResults'] = max_results
    if fields:
        params['fields'] = fields
    if expand:
        params['expand'] = expand
    return await jira_request(endpoint="/search", method="GET", params=params)

@jira_mcp.tool()
async def get_project(project_id_or_key: str) -> Dict[str, Any]:
    """특정 프로젝트 정보 조회 (GET /rest/api/3/project/{projectIdOrKey})"""
    return await jira_request(endpoint=f"/project/{project_id_or_key}", method="GET")

@jira_mcp.tool()
async def list_projects(start_at: Optional[int] = None, max_results: Optional[int] = None, expand: Optional[str] = None) -> Dict[str, Any]:
    """모든 프로젝트 목록 조회 (GET /rest/api/3/project)"""
    params = {}
    if start_at is not None:
        params['startAt'] = start_at
    if max_results is not None:
        params['maxResults'] = max_results
    if expand:
        params['expand'] = expand
    return await jira_request(endpoint="/project", method="GET", params=params if params else None)

@jira_mcp.tool()
async def get_edit_issue_meta(issue_id_or_key: str) -> Dict[str, Any]:
    """이슈 편집을 위한 메타데이터 조회 (GET /rest/api/3/issue/{issueIdOrKey}/editmeta)"""
    return await jira_request(endpoint=f"/issue/{issue_id_or_key}/editmeta", method="GET")

@jira_mcp.tool()
async def add_watchers(issue_id_or_key: str, account_id: str) -> Dict[str, Any]:
    """이슈에 워처 추가 (POST /rest/api/3/issue/{issueIdOrKey}/watchers). The request body should be the account ID of the user to add."""
    # Jira API for adding a watcher expects the accountId directly in the body, not as JSON.
    # httpx's json parameter will quote it, so we use 'content' for raw string body.
    # However, the API docs also state Content-Type: application/json is required.
    # This is a bit tricky. Let's try sending it as JSON string as per Atlassian community answers.
    return await jira_request(endpoint=f"/issue/{issue_id_or_key}/watchers", method="POST", json_data=account_id)

@jira_mcp.tool()
async def remove_watcher(issue_id_or_key: str, account_id: str) -> Dict[str, Any]:
    """이슈에서 특정 워처 제거 (DELETE /rest/api/3/issue/{issueIdOrKey}/watchers?accountId={accountId}) Note: API docs mention username or key, but accountId is preferred."""
    params = {"accountId": account_id}
    return await jira_request(endpoint=f"/issue/{issue_id_or_key}/watchers", method="DELETE", params=params)

@jira_mcp.tool()
async def get_attachment_metadata(attachment_id: str) -> Dict[str, Any]:
    """첨부 파일 메타데이터 조회 (GET /rest/api/3/attachment/{id})"""
    return await jira_request(endpoint=f"/attachment/{attachment_id}", method="GET")

@jira_mcp.tool()
async def create_remote_link(issue_id_or_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """이슈에 외부 링크 추가 (POST /rest/api/3/issue/{issueIdOrKey}/remotelink)"""
    return await jira_request(endpoint=f"/issue/{issue_id_or_key}/remotelink", method="POST", json_data=payload)



@jira_mcp.tool()
async def download_attachment(attachment_url: str) -> bytes:
    """첨부 파일 다운로드 (GET attachment content URL)
    The URL should be the 'content' URL from the attachment metadata.
    Example: https://your-domain.atlassian.net/secure/attachment/10000/filename.txt
    """
    # The attachment_url is a full URL, not a relative endpoint
    return await jira_request(
        endpoint_or_url=attachment_url,
        method="GET",
        expect_json=False # We expect raw file content
    )

if __name__ == "__main__":

    if not ATLASSIAN_DOMAIN or not JIRA_USER_EMAIL or not JIRA_API_TOKEN:
        print("Error: ATLASSIAN_DOMAIN, JIRA_USER_EMAIL, and JIRA_API_TOKEN environment variables must be set.")
        print("Please set them before running the server.")
        print("Example: export ATLASSIAN_DOMAIN=\"your-domain.atlassian.net\"")
        print("Example: export JIRA_USER_EMAIL=\"user@example.com\"")
        print("Example: export JIRA_API_TOKEN=\"your_jira_api_token\"")
    else:
        print(f"Jira MCP server running for domain: {ATLASSIAN_DOMAIN}, user: {JIRA_USER_EMAIL}")
        print("Available tools:")
        for tool_name in jira_mcp.tools:
            print(f"- {tool_name}")
        jira_mcp.run(transport="sse")
