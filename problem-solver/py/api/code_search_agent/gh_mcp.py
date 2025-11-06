import os
import re
from fastmcp import Client
from dotenv import load_dotenv

load_dotenv()
GITHUB_PAT = os.getenv("GITHUB_PAT")

config = {
    "mcpServers": {
        "github": {
            "transport": "stdio",
            "command": "docker",
            "args": [
                "run", "--rm", "-i",
                "-e", f"GITHUB_PERSONAL_ACCESS_TOKEN={GITHUB_PAT}",
                "ghcr.io/github/github-mcp-server:latest"
            ]
        }
    }
}
client = Client(config)

async def get_repos_from_github_mcp(query, limit=5):

    result = await client.call_tool(
        "search_repositories",
        {
            "query": query,
            "per_page": limit,
            "sort": "stars",
            "order": "desc"
        }
    )
    text = result.content[0].text if result.content else ""
    urls = re.findall(r"https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+", text)
    return urls[:limit]