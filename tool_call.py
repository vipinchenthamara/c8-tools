"""Part 1: a complete Groq tool-call loop. Run: python tool_call.py [question]."""
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
import requests
from lookups import LECTURE_DESCRIPTION, SECURITY_DESCRIPTION, lookup_lecture, lookup_security_term

load_dotenv(Path(__file__).with_name(".env"))
DEFAULT_QUESTION = "When is Lecture 12 of 100xEngineers Cohort 8, and what is it about?"


def get_lecture(number: int) -> dict:
    """Look up a lecture in the 100xEngineers Cohort 8 course sheet."""
    return lookup_lecture(number)


def get_security_term(term: str) -> dict:
    """Look up a term in the project's cybersecurity study glossary CSV."""
    return lookup_security_term(term)


# These cards tell the model when to request each function.
card = {"type": "function", "function": {
    "name": "get_lecture",
    "description": LECTURE_DESCRIPTION,
    "parameters": {
        "type": "object",
        "properties": {"number": {
            "type": "integer", "minimum": 1, "maximum": 19,
            "description": "The Cohort 8 lecture/class/session number, from 1 to 19.",
        }},
        "required": ["number"], "additionalProperties": False,
    },
}}
security_card = {"type": "function", "function": {
    "name": "get_security_term",
    "description": SECURITY_DESCRIPTION,
    "parameters": {
        "type": "object",
        "properties": {"term": {
            "type": "string", "description": "A glossary term or abbreviation, such as MFA or SIEM.",
        }},
        "required": ["term"], "additionalProperties": False,
    },
}}
TOOLS = [card, security_card]
FUNCTIONS = {"get_lecture": get_lecture, "get_security_term": get_security_term}


def ask_model(messages, tools=None):
    """Send exactly these messages and optional tool cards to Groq."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        raise RuntimeError("No GROQ_API_KEY found. Add GROQ_API_KEY=your key to .env next to tool_call.py.")
    body = {"model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
            "messages": messages, "temperature": 0}
    if tools:
        body["tools"] = tools
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": "Bearer " + key}, json=body, timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]


def execute_tool(call):
    """Dispatch only known tools; return argument errors to the model as data."""
    name = call["function"]["name"]
    if name not in FUNCTIONS:
        return {"error": f"Unknown tool: {name}"}
    try:
        args = json.loads(call["function"]["arguments"])
        if not isinstance(args, dict):
            return {"error": "Tool arguments must be a JSON object."}
        return FUNCTIONS[name](**args)
    except (ValueError, TypeError) as exc:
        return {"error": f"Invalid tool arguments: {exc}"}


def run_question(question, *, model=None, on_tool=None, max_rounds=8):
    """Run every requested tool, then ask again until there is a final answer."""
    model = model or ask_model
    messages = [{"role": "user", "content": question}]
    calls = []
    reply = model(messages, TOOLS)
    rounds = 0
    while reply.get("tool_calls"):
        if rounds >= max_rounds:
            raise RuntimeError(f"Stopped after {max_rounds} tool rounds without a final answer.")
        rounds += 1
        messages.append(reply)
        for call in reply["tool_calls"]:
            result = execute_tool(call)
            event = {"name": call["function"]["name"],
                     "arguments": call["function"]["arguments"], "result": result}
            calls.append(event)
            if on_tool:
                on_tool(event)
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(result, ensure_ascii=False)})
        reply = model(messages, TOOLS)
    return {"answer": reply.get("content") or "", "tool_calls": calls}


def main():
    question = " ".join(sys.argv[1:]) or DEFAULT_QUESTION
    try:
        result = run_question(question, on_tool=lambda event: print(
            f"The model asked for: {event['name']} {event['arguments']}", file=sys.stderr))
    except (RuntimeError, requests.RequestException) as exc:
        raise SystemExit(str(exc)) from exc
    print(result["answer"])


if __name__ == "__main__":
    main()
