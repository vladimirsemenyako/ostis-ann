import os
from fastmcp import Client
from dotenv import load_dotenv
import re

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

config = {
    "mcpServers": {
        "huggingface": {
            "transport": "http",
            "url": "https://huggingface.co/mcp",
            "headers": {
                "Authorization": f"Bearer {HF_TOKEN}",
                "Accept": "application/json, text/event-stream"
            }
        }
    }
}


async def get_response_from_hf_mcp(query, limit=1):
    client = Client(config)

    async with client:
        result = await client.call_tool(
        "model_search",
        {"query": query, "limit": limit, "sort": "downloads"}
        )
    text = result.content[0].text
    links = []
    urls = re.findall(r"\(https://hf.+\)",text)
    for url in urls:
        links.append(url[1:-1])
    return links
