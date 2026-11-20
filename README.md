# C8 Tools: lecture lookup and cybersecurity glossary

This is my completed **100xEngineers Cohort 8, Practice Set 3** project: a Python tool-calling application and a deployed MCP server. It demonstrates how an AI model requests a function, how Python executes it, and how the same functions can be offered to other applications through **MCP (Model Context Protocol)**.

The project was completed with **Codex assistance** for implementation, testing, documentation, and deployment setup. I selected the cybersecurity glossary topic and completed the credential and account setup. **Google Antigravity was not used.** The server is hosted on **FastMCP Gateway by Prefect**, at `horizon.prefect.io`.

## Try the deployed project

**For a browser demonstration:** open [ChatMCP](https://horizon.prefect.io/vipin-c8-tools/servers/vipin-c8-tools/chat), sign in to the project owner's Gateway account, and ask:

- “When is Lecture 12 of 100xEngineers Cohort 8, and what is it about?”
- “Look up MFA in the project glossary.”

**For an MCP-compatible application:** use this public server address:

```text
https://vipin-c8-tools.fastmcp.app/mcp
```

The `/mcp` address is a protocol endpoint. Opening it directly in a browser can return **405 Method Not Allowed**. Use ChatMCP for the browser demo, or enter the endpoint in an MCP client's server URL field. Public tool calls do not require authentication.

## What I implemented

Starting from the [course starter repository](https://github.com/Siddhant-Goswami/c8-tools), which supplied the lecture lookup and Groq request function, I completed the following with Codex assistance:

1. **Described the lecture tool:** completed its tool card with its purpose and required lecture number.
2. **Built the tool-call loop:** parse Groq's function arguments, execute each requested function, send its result back with the matching call ID, and continue until the model answers. General questions can be answered without a tool.
3. **Added a custom data tool:** created an eight-entry cybersecurity glossary CSV and a lookup that accepts names and aliases such as MFA and SIEM.
4. **Exposed both functions through MCP:** registered them with FastMCP, using descriptions and annotated input types for discovery.
5. **Tested the implementation:** checked the loop and lookups, ran ten real Groq questions, and saved the observed tool calls and answers.
6. **Deployed and verified the server:** connected the fork to FastMCP Gateway and called both tools through an unauthenticated client and ChatMCP.

The completed loop also handles unknown tool names, malformed arguments, multiple calls, repeated rounds, and a maximum of eight tool rounds.

## How the two parts work

### Part 1: Groq requests functions in the local Python program

```text
Question → Groq → function request → Python lookup → result sent to Groq → answer
```

[`tool_call.py`](tool_call.py) sends the system instructions, question, and tool cards to Groq. The model chooses whether to request a function; Python performs the lookup. This program calls the Python functions directly.

### Part 2: an MCP client calls the hosted Python tools

```text
MCP client (for example, ChatMCP) → hosted FastMCP server → Python lookup → result
```

[`mcp_server.py`](mcp_server.py) exposes the same two lookups through MCP. A client discovers the tool schemas and calls them. The server itself does not run Groq and does not need a Groq API key. The Part 1 script does not connect to this deployed MCP endpoint.

Both parts use [`lookups.py`](lookups.py) so their lookup behavior stays consistent.

## Tools and data

| Tool | Input | Data source | Returned information |
|---|---|---|---|
| `get_lecture` | Lecture number, 1–19 | The course's existing public Google Sheet | Date, title, session type, and tools |
| `get_security_term` | Term or abbreviation, such as MFA | [Project glossary CSV](data/security_glossary.csv) | Term, category, definition, and example |

The glossary is a small project-authored study dataset. Matching ignores case and repeated whitespace and accepts aliases. A missing term returns an explicit error and the available terms. The public server exposes the course sheet and study glossary; the Groq key is stored locally in an ignored `.env` file.

## Which service does what?

| Component | Role in this project |
|---|---|
| Codex | Assistance with writing, testing, documenting, and deploying the project |
| GitHub | Stores this fork and its source code |
| Groq | Runs the model used by the Part 1 Python program |
| FastMCP | Python framework that exposes the two functions through MCP |
| FastMCP Gateway by Prefect | Hosts the MCP server online and provides ChatMCP for testing |
| Google Antigravity | Not used in this implementation or deployment |

## Run it locally

Use Python 3.12 for the setup verified for this project. From the cloned repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Run the Groq tool-calling program

On first setup, copy the environment template and edit `.env` to set your own `GROQ_API_KEY`. Keep that file out of Git.

```bash
cp .env.example .env
python tool_call.py
python tool_call.py "What is an API?"
python tool_call.py "Look up MFA in my project glossary."
```

The default model is `openai/gpt-oss-120b`, served by Groq. Set `GROQ_MODEL` in `.env` to change it.

### Run the MCP server

This part does not require a Groq key:

```bash
python mcp_server.py
```

In a second terminal, activate the same virtual environment and run:

```bash
source .venv/bin/activate
fastmcp list http://localhost:8000/mcp --input-schema
fastmcp call http://localhost:8000/mcp get_lecture number=12
fastmcp call http://localhost:8000/mcp get_security_term term=MFA
```

The default port is 8000; set `PORT` to use another port.

## Verification and observed results

The recorded checks were run on **20 November 2026**:

| Check | Recorded result | Evidence |
|---|---|---|
| Automated tests | 17 passed | [Test suite](tests/test_assignment.py) |
| Live Groq evaluations | 10/10 questions selected the expected tools or correctly selected none | [Model answers, arguments, and tool results](evaluation_results.json) |
| Public MCP client | Discovered both tools; fetched Lecture 12 and MFA; checked a missing term | [Deployment verification](deployment_verification.json) |
| ChatMCP | Called both deployed tools and returned the Lecture 12 fields and MFA entry | [Recorded observation](deployment_verification.json) |

The ten model cases evaluate **the final system instructions and both tool cards together**. The score measures tool selection; it is not a claim of perfect answer accuracy. The saved answers were also reviewed against the returned data.

### Course lecture questions

<!-- lecture-evaluation:start -->
| Question | Should it ask for the tool? | Did it? |
|---|---|---|
| When is Lecture 12 of 100xEngineers Cohort 8, and what is it about? | get_lecture | get_lecture (matched) |
| Which tools do we use in the seventh class? | get_lecture | get_lecture (matched) |
| What is an API? | No | No (matched) |
| Is session ten a combined one or separate? | get_lecture | get_lecture (matched) |
| In lecture 3 of Harvard CS50, which language is taught? | No | No (matched) |
<!-- lecture-evaluation:end -->

### Custom glossary questions

<!-- glossary-evaluation:start -->
| Question | Should it ask for the tool? | Did it? |
|---|---|---|
| According to my project glossary, what is MFA? Give its example. | get_security_term | get_security_term (matched) |
| Look up SIEM in my cybersecurity study notes. | get_security_term | get_security_term (matched) |
| What does the project glossary say about least privilege? | get_security_term | get_security_term (matched) |
| Does my project glossary contain quantum firewall? | get_security_term | get_security_term (matched) |
| What is 2 + 2? | No | No (matched) |
<!-- glossary-evaluation:end -->

### Repeat the checks

```bash
python -m pytest -q
# Requires a Groq key; makes live model requests and updates both tables:
python evaluate.py --update-readme
# Calls the public server without authentication:
python verify_mcp.py https://vipin-c8-tools.fastmcp.app/mcp
```

To verify a running local server, use `python verify_mcp.py http://localhost:8000/mcp`.

## Deployment and submission

| Item | Value |
|---|---|
| GitHub fork to submit | [vipinchenthamara/c8-tools](https://github.com/vipinchenthamara/c8-tools) |
| MCP endpoint to submit | [https://vipin-c8-tools.fastmcp.app/mcp](https://vipin-c8-tools.fastmcp.app/mcp) |
| Hosting service | FastMCP Gateway by Prefect |
| Repository branch | `main` |
| Server entrypoint | `mcp_server.py:mcp` |
| Dependency file | `requirements.txt` |
| Endpoint authentication | Off, for the assignment's public read-only tools |

[Manage the deployment](https://horizon.prefect.io/vipin-c8-tools/servers/vipin-c8-tools/deployments) with the project owner's Gateway account. Gateway imports the server object and manages its HTTP listener. It rebuilds the deployment when `main` changes.

**Submit the GitHub fork and MCP endpoint links on the LMS.** Preparing this repository did not submit it to the LMS.

## Files to explore

| File | Purpose |
|---|---|
| [`tool_call.py`](tool_call.py) | Groq request, tool cards, and tool execution loop |
| [`mcp_server.py`](mcp_server.py) | MCP tool registration and local HTTP server |
| [`lookups.py`](lookups.py) | Shared lecture and glossary lookup functions |
| [`data/security_glossary.csv`](data/security_glossary.csv) | Custom glossary entries and aliases |
| [`evaluate.py`](evaluate.py) | Runs the ten model questions and updates the README tables |
| [`verify_mcp.py`](verify_mcp.py) | Checks discovery and calls against an MCP endpoint |
| [`tests/test_assignment.py`](tests/test_assignment.py) | Automated checks without live model requests |
| [`docs/ASSIGNMENT.md`](docs/ASSIGNMENT.md) | Original starter instructions, kept as a historical reference |

The original assignment is preserved separately so its intermediate steps and intentionally incomplete examples are not confused with this completed implementation.
