from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server for VirusTotal
virustotal_mcp = FastMCP("virustotal")

VIRUSTOTAL_API_BASE = "https://www.virustotal.com/api/v3"
# TODO: 실제 API 키를 환경변수 등에서 안전하게 불러오세요.
VIRUSTOTAL_API_KEY = ""

async def vt_request(endpoint: str) -> dict[str, Any] | None:
    headers = {
        "x-apikey": VIRUSTOTAL_API_KEY,
        "Accept": "application/json",
    }
    url = f"{VIRUSTOTAL_API_BASE}{endpoint}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

@virustotal_mcp.tool()
async def get_ip_info(ip: str) -> str:
    """Get VirusTotal report for an IP address.

    Args:
        ip: IP address to query (e.g. 8.8.8.8)
    """
    data = await vt_request(f"/ip_addresses/{ip}")
    if not data or "error" in data:
        return f"Unable to fetch IP info: {data.get('error', 'Unknown error')}"
    # 간단 요약만 반환 (필요시 상세 포맷 추가)
    attr = data.get("data", {}).get("attributes", {})
    last_analysis_stats = attr.get("last_analysis_stats", {})
    country = attr.get("country", "Unknown")
    as_owner = attr.get("as_owner", "Unknown")
    return (
        f"IP: {ip}\n"
        f"Country: {country}\n"
        f"AS Owner: {as_owner}\n"
        f"Malicious: {last_analysis_stats.get('malicious', 0)}\n"
        f"Suspicious: {last_analysis_stats.get('suspicious', 0)}\n"
        f"Harmless: {last_analysis_stats.get('harmless', 0)}\n"
        f"Undetected: {last_analysis_stats.get('undetected', 0)}\n"
    )

if __name__ == "__main__":
    virustotal_mcp.run(transport="sse") 