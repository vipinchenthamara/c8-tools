"""Verify discovery and both tools against a running local or deployed MCP endpoint."""
import argparse
import asyncio
import json

from fastmcp import Client


async def verify(url):
    async with Client(url, auth=None) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        assert {"get_lecture", "get_security_term"} <= set(tools), "Expected both assignment tools"
        lecture = await client.call_tool("get_lecture", {"number": 12})
        glossary = await client.call_tool("get_security_term", {"term": "MFA"})
        missing = await client.call_tool("get_security_term", {"term": "quantum firewall"})
        assert lecture.data["title"].startswith("12."), lecture.data
        assert glossary.data["term"] == "Multi-factor authentication", glossary.data
        assert "error" in missing.data, missing.data
        print(json.dumps({"endpoint": url, "tools": sorted(tools),
                          "lecture_12": lecture.data, "MFA": glossary.data,
                          "missing_term": missing.data}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?", default="http://localhost:8000/mcp")
    asyncio.run(verify(parser.parse_args().url))
