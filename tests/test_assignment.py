"""Offline checks: tool-loop behavior, data failures, and actual MCP discovery/calls."""
import asyncio
import json
from unittest.mock import Mock

from fastmcp import Client
import pytest
import requests

import lookups
from mcp_server import mcp
import tool_call


def tool_request(name, arguments, call_id="call_1"):
    return {"id": call_id, "type": "function",
            "function": {"name": name, "arguments": json.dumps(arguments)}}


def test_model_can_answer_without_a_tool():
    model = Mock(return_value={"role": "assistant", "content": "An API is an interface."})
    result = tool_call.run_question("What is an API?", model=model)
    assert result == {"answer": "An API is an interface.", "tool_calls": []}
    assert model.call_count == 1


def test_multiple_tools_return_matching_ids_before_next_model_turn():
    calls = [tool_request("get_security_term", {"term": "MFA"}, "a"),
             tool_request("get_security_term", {"term": "SIEM"}, "b")]
    turns = []

    def model(messages, tools):
        turns.append(list(messages))
        if len(turns) == 1:
            return {"role": "assistant", "content": None, "tool_calls": calls}
        assert [message["tool_call_id"] for message in messages[-2:]] == ["a", "b"]
        assert json.loads(messages[-2]["content"])["term"] == "Multi-factor authentication"
        assert json.loads(messages[-1]["content"])["category"] == "Monitoring"
        return {"role": "assistant", "content": "Both entries found."}

    result = tool_call.run_question("Look up MFA and SIEM in my glossary.", model=model)
    assert result["answer"] == "Both entries found."
    assert len(result["tool_calls"]) == 2
    assert turns[1][1]["tool_calls"] == calls


def test_loop_handles_more_than_one_round():
    replies = [
        {"role": "assistant", "tool_calls": [tool_request("get_security_term", {"term": "MFA"})]},
        {"role": "assistant", "tool_calls": [tool_request("get_security_term", {"term": "SIEM"}, "second")]},
        {"role": "assistant", "content": "Done"},
    ]
    result = tool_call.run_question("Two lookups", model=Mock(side_effect=replies))
    assert result["answer"] == "Done"
    assert len(result["tool_calls"]) == 2


def test_loop_is_bounded():
    reply = {"role": "assistant", "tool_calls": [tool_request("get_security_term", {"term": "MFA"})]}
    with pytest.raises(RuntimeError, match="2 tool rounds"):
        tool_call.run_question("Repeat forever", model=Mock(return_value=reply), max_rounds=2)


@pytest.mark.parametrize("name,args", [
    ("unknown_function", {}),
    ("get_lecture", {"unexpected": 12}),
    ("get_security_term", []),
])
def test_bad_tool_requests_return_errors(name, args):
    assert "error" in tool_call.execute_tool(tool_request(name, args))


def test_malformed_json_returns_error():
    call = tool_request("get_lecture", {})
    call["function"]["arguments"] = "{bad json"
    assert "error" in tool_call.execute_tool(call)


@pytest.mark.parametrize("number", [0, 20, True, "12"])
def test_lecture_validates_before_network(monkeypatch, number):
    fetch = Mock()
    monkeypatch.setattr(lookups.requests, "get", fetch)
    assert "error" in lookups.lookup_lecture(number)
    fetch.assert_not_called()


def test_lecture_skips_short_rows_and_strips_cells(monkeypatch):
    response = Mock(text='Header\n"Sat 14 Nov 2026","12. Building with tools","separate practical","Python "\n')
    monkeypatch.setattr(lookups.requests, "get", Mock(return_value=response))
    result = lookups.lookup_lecture(12)
    assert result["tools"] == "Python"
    assert result["date"] == "Sat 14 Nov 2026"


def test_lecture_network_failure_is_explicit(monkeypatch):
    monkeypatch.setattr(lookups.requests, "get", Mock(side_effect=requests.Timeout))
    assert "could not be fetched" in lookups.lookup_lecture(12)["error"]


def test_html_instead_of_sheet_is_explicit(monkeypatch):
    monkeypatch.setattr(lookups.requests, "get", Mock(return_value=Mock(text="<html>Sign in</html>")))
    assert "expected lecture CSV" in lookups.lookup_lecture(12)["error"]


def test_glossary_alias_case_and_missing_entry():
    assert lookups.lookup_security_term("  mFa  ")["category"] == "Identity"
    assert lookups.lookup_security_term("principle of least privilege")["term"] == "Least privilege"
    result = lookups.lookup_security_term("quantum firewall")
    assert "error" in result
    assert "Least privilege" in result["available_terms"]
    assert "error" in lookups.lookup_security_term(" ")


def test_actual_mcp_discovery_call_and_input_validation(monkeypatch):
    response = Mock(text='"Sat 14 Nov 2026","12. Building with tools","separate practical","Python"\n')
    monkeypatch.setattr(lookups.requests, "get", Mock(return_value=response))

    async def check():
        async with Client(mcp) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert set(tools) == {"get_lecture", "get_security_term"}
            assert tools["get_lecture"].input_schema["properties"]["number"]["type"] == "integer"
            assert tools["get_security_term"].description == lookups.SECURITY_DESCRIPTION
            glossary = await client.call_tool("get_security_term", {"term": "MFA"})
            assert glossary.data["term"] == "Multi-factor authentication"
            lecture = await client.call_tool("get_lecture", {"number": 12})
            assert lecture.data["title"].startswith("12.")
            with pytest.raises(Exception):
                await client.call_tool("get_lecture", {"number": "not an integer"})
    asyncio.run(check())
