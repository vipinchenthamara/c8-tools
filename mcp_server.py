"""Part 2: the same two lookups over MCP. Run: python mcp_server.py."""
import os
from typing import Annotated

from fastmcp import FastMCP
from lookups import LECTURE_DESCRIPTION, SECURITY_DESCRIPTION, lookup_lecture, lookup_security_term

mcp = FastMCP("100x curriculum and cybersecurity study glossary")


@mcp.tool(description=LECTURE_DESCRIPTION,
          annotations={"readOnlyHint": True, "destructiveHint": False})
def get_lecture(number: Annotated[int, "The Cohort 8 lecture/class/session number, from 1 to 19."]) -> dict:
    """Look up the schedule, title, session type and tools for a Cohort 8 lecture."""
    return lookup_lecture(number)


@mcp.tool(description=SECURITY_DESCRIPTION,
          annotations={"readOnlyHint": True, "destructiveHint": False})
def get_security_term(term: Annotated[str, "A term or abbreviation from the project glossary, such as MFA or SIEM."]) -> dict:
    """Read a definition, category and example from the project's cybersecurity glossary CSV."""
    return lookup_security_term(term)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
