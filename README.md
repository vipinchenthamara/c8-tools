# C8 Tools: tool calling and an MCP server

Implemented the full tool loop and two read-only MCP tools: `get_lecture` (live course sheet) and `get_security_term` (local cybersecurity glossary). The loop handles direct answers, multiple tool requests, repeated rounds, malformed arguments, unknown tools, and a bounded number of rounds. Both entrypoints share the same lookup functions and tool descriptions.

## Run the completed implementation

Use Python 3.12 or newer. The dependencies in `requirements.txt` are the versions verified locally.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env and set GROQ_API_KEY. Never commit the key.
python tool_call.py
python tool_call.py "What is an API?"
python tool_call.py "Look up MFA in my project glossary."
```

The MCP server itself does **not** need a Groq key:

```bash
python mcp_server.py
# In a second terminal with the virtual environment active:
fastmcp list http://localhost:8000/mcp --input-schema
fastmcp call http://localhost:8000/mcp get_lecture number=12
fastmcp call http://localhost:8000/mcp get_security_term term=MFA
python verify_mcp.py http://localhost:8000/mcp
```

Set `PORT` to change the local port. FastMCP Gateway imports `mcp_server.py:mcp` and manages the HTTP listener itself.

## Verification and submission status

- Offline suite: 17 tests passed, covering tool-loop behavior, invalid requests, data errors, and MCP discovery/calls.
- Live course sheet: Lecture 12 returned successfully.
- Local HTTP MCP: discovery and both tool calls verified; a missing glossary term returned an explicit error.
- Groq model evaluations: **not run yet** because no Groq key is configured. The two tables below show predictions, not invented observations.
- Public MCP deployment: **pending Gateway account verification**. No deployed URL is claimed yet.

```bash
python -m pytest -q
python evaluate.py --update-readme
```

`evaluate.py` runs all ten questions against Groq, saves the actual model answers, arguments, and tool results in `evaluation_results.json`, and fills both README tables. A mismatch or API failure produces a nonzero exit status. Review the answers and results as well as the tool selection before submitting.

## Deploy this fork on FastMCP Gateway

1. Sign in at [FastMCP Gateway](https://horizon.prefect.io), verify your email, and connect GitHub if requested.
2. Select **vipinchenthamara/c8-tools**, branch **main**.
3. Use entrypoint **mcp_server.py:mcp**. Dependencies are detected from `requirements.txt`.
4. For the assignment's public read-only endpoint, choose authentication off. The server exposes only the course sheet and study glossary; do not add private data to a public endpoint.
5. Deploy, copy the real `https://...fastmcp.app/mcp` URL, and verify it:

```bash
python verify_mcp.py https://YOUR-SERVER.fastmcp.app/mcp
fastmcp call https://YOUR-SERVER.fastmcp.app/mcp get_security_term term=MFA
```

Open ChatMCP on the server page and ask about Lecture 12 and an MFA glossary entry. Submit the fork link and the verified public endpoint on the LMS after the live model tables are filled.

---

The original practice-set instructions are retained below for reference.

# Practice set 3: your first tool call, then an MCP server

On the [Tool Bench](https://100x-curriculum.vercel.app/c8/module-2/lecture-11-tool-calling-and-mcp/bench) you pressed buttons. Here you write the code behind each button, on the same course sheet, then put the tool on the internet.

Due before Lecture 13, Fri 20 Nov 2026.

| On the bench | Here |
|---|---|
| The sheet | `get_lecture(number)`, given |
| The model | `ask_model(messages, tools)`, given |
| Your server | The bottom of `tool_call.py`. You write it in Part 1 |
| The sheet's server | `mcp_server.py`. You write it in Part 2 |

## Setup

1. Press **Fork** at the top of this page, then clone your fork and open it in your editor.
2. Install what the two files need:
   ```bash
   pip install -r requirements.txt
   ```
3. Make a file called `.env` next to `tool_call.py` with one line: `GROQ_API_KEY=your key`. It is the key you used on the bench. `.env` never goes to GitHub.

## Part 1: the tool call

Everything happens at the bottom of `tool_call.py`. After every step, run `python tool_call.py`.

### Step 1. Ask without a card

Change nothing. Run it.

**You should see** one message from the model. It guesses, or says it cannot know. Nothing went to the sheet.

### Step 2. Write the card

The card on the bench had three fields. The same three are in `card`:

| On the bench | In `card` |
|---|---|
| Name | `"name"` |
| Use it when | the first `"description"` |
| It needs | the `"description"` under `number` |

1. Fill in the two empty strings. Use the card you wrote on the bench.
2. Send the card with the question: change `ask_model(messages)` to `ask_model(messages, [card])`.

**You should see** no answer. The model wrote a request and stopped:

```json
"tool_calls": [{
  "id": "fc_7217...",
  "type": "function",
  "function": {"name": "get_lecture", "arguments": "{\"number\":12}"}
}]
```

### Step 3. Run the request

On the bench you pressed a button to run it. Now your code does. Under `# Step 3`:

1. Take the first request out of `reply["tool_calls"]`.
2. Its arguments are text. Turn them into a dictionary with `json.loads`.
3. Call `get_lecture` with them and print the result.

**You should see** the row:

```
{'date': 'Sat 14 Nov 2026', 'title': '12. Building with tool calling and MCP', 'type': 'separate practical', 'tools': 'Python, Groq, FastMCP '}
```

<details><summary>Stuck?</summary>

```python
call = reply["tool_calls"][0]
args = json.loads(call["function"]["arguments"])
result = get_lecture(**args)
print(result)
```
</details>

### Step 4. Hand the row back

Your code has the row. The model still has nothing. Under `# Step 4`:

1. Add the model's request to `messages`.
2. Add the result to `messages`. This is the message you saw on the wire:
   ```json
   {"role": "tool", "tool_call_id": "the id of the request", "content": "the result, as text"}
   ```
3. Ask the model again, with the card, and print `reply["content"]`.

**You should see** the answer, with the date and title from the sheet. That is one full tool call.

<details><summary>Stuck?</summary>

```python
messages.append(reply)
messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
reply = ask_model(messages, [card])
print(reply["content"])
```
</details>

### Step 5. Let your code carry it

Run `python tool_call.py "What is an API?"`. It crashes: the model answered on its own, so there is no request to run.

Turn steps 3 and 4 into a loop: **while** the reply has `tool_calls`, run each one and hand the result back. When it has none, print the answer. Delete the `print(json.dumps(...))` line while you are there.

**You should see** both of these work:

```bash
python tool_call.py                      # asks for the tool, then answers
python tool_call.py "What is an API?"    # answers on its own
```

<details><summary>Stuck?</summary>

```python
reply = ask_model(messages, [card])

while reply.get("tool_calls"):
    messages.append(reply)
    for call in reply["tool_calls"]:
        args = json.loads(call["function"]["arguments"])
        print("The model asked for: get_lecture", args)
        result = get_lecture(**args)
        messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
    reply = ask_model(messages, [card])

print("\n" + reply["content"])
```
</details>

### Step 6. Test the card

The model reads only the card. First fill in the middle column. Then run each question and fill in the last one.

<!-- lecture-evaluation:start -->
| Question | Should it ask for the tool? | Did it? |
|---|---|---|
| When is Lecture 12 of 100xEngineers Cohort 8, and what is it about? | get_lecture | Not run: needs Groq key |
| Which tools do we use in the seventh class? | get_lecture | Not run: needs Groq key |
| What is an API? | No | Not run: needs Groq key |
| Is session ten a combined one or separate? | get_lecture | Not run: needs Groq key |
| In lecture 3 of Harvard CS50, which language is taught? | No | Not run: needs Groq key |
<!-- lecture-evaluation:end -->

```bash
python tool_call.py "Which tools do we use in the seventh class?"
```

If a row does not match, change one thing in the card and run it again. Edit this table in your fork: it is part of what you submit.

## Part 2: the MCP server

The card and the function live inside `tool_call.py`. A second app would need a copy of both. So move them to the sheet's side, once.

### Step 1. Move the function

Copy `get_lecture` from `tool_call.py` into `mcp_server.py`. Put `@mcp.tool` on the line above `def`.

### Step 2. Write the card into the function

There is no `card` dictionary here. FastMCP writes it from the function:

| On the bench | In the function |
|---|---|
| Name | the function's name |
| Use it when | the docstring, the `"""text"""` on the first line inside the function |
| It needs | the type hint: `number: Annotated[int, "what the number is"]` |

Add both, in your own words from Part 1.

<details><summary>Stuck?</summary>

```python
@mcp.tool
def get_lecture(number: Annotated[int, "The lecture number, 1 to 19."]) -> dict:
    """Your 'Use it when' text from Part 1."""
    for row in csv.reader(io.StringIO(requests.get(SHEET).text)):
        ...
```
</details>

### Step 3. Switch it on

```bash
python mcp_server.py
```

Leave it running. In a second terminal, ask it what it offers, then call the tool:

```bash
fastmcp list http://localhost:8000/mcp --input-schema
fastmcp call http://localhost:8000/mcp get_lecture number=12
```

**You should see** your card come back from the first command, and the Lecture 12 row from the second. No model is involved: any app that speaks MCP can do what those two commands did.

### Step 4. Put it on the internet

`localhost` works only on your laptop. [FastMCP Gateway](https://horizon.prefect.io) runs the file for you, free for personal projects.

1. Push your work:
   ```bash
   git add -A
   git commit -m "My tool call and MCP server"
   git push
   ```
2. Open [horizon.prefect.io](https://horizon.prefect.io) and sign in with GitHub.
3. Pick your fork of `c8-tools`.
4. Entrypoint: `mcp_server.py:mcp`. That is the file, then the variable that holds the server.
5. Leave **Authentication** off, so any app can connect.
6. Press **Deploy Server**. It takes about a minute.

**You should see** an address like `https://your-server-name.fastmcp.app/mcp`.

### Step 5. Call it from anywhere

The same two commands, with the new address:

```bash
fastmcp list https://your-server-name.fastmcp.app/mcp
fastmcp call https://your-server-name.fastmcp.app/mcp get_lecture number=12
```

Then open **ChatMCP** on your server's Gateway page and ask it about Lecture 12. That is a second app using your tool. You wrote no code for it.

## Now your own data

Do it once more with data you care about: your own Google Sheet, a CSV file, a Supabase table, or an API from this course.

1. Write your own function next to `get_lecture`, in both files.
2. Write its card, and five questions of your own for the table in step 6.
3. Push, and call your new tool at the deployed address.

### Custom dataset: cybersecurity study glossary

`data/security_glossary.csv` is a small, project-authored study dataset with eight terms, aliases, categories, definitions, and examples. It contains no private account data. Edit the CSV to personalize it. The `get_security_term(term)` function is exposed in both Python entrypoints; shared CSV lookup logic lives in `lookups.py`. Matching ignores case and repeated whitespace and accepts aliases such as MFA and SIEM. Unknown terms return an explicit error and the available terms.

<!-- glossary-evaluation:start -->
| Question | Should it ask for the tool? | Did it? |
|---|---|---|
| According to my project glossary, what is MFA? Give its example. | get_security_term | Not run: needs Groq key |
| Look up SIEM in my cybersecurity study notes. | get_security_term | Not run: needs Groq key |
| What does the project glossary say about least privilege? | get_security_term | Not run: needs Groq key |
| Does my project glossary contain quantum firewall? | get_security_term | Not run: needs Groq key |
| What is 2 + 2? | No | Not run: needs Groq key |
<!-- glossary-evaluation:end -->

## Submit it

- The link to your fork, with the step 6 table filled in.
- Your deployed address.

Once you're done, submit it on the LMS. We go through them in the office hour.

## If something goes wrong

| You see | Fix |
|---|---|
| `No GROQ_API_KEY found` | Make the `.env` file from Setup, next to `tool_call.py` |
| `429` from Groq | You hit the free rate limit. Wait a minute and run again |
| `400` from Groq | The model wrote its request badly. It predicts, so that can happen. Run again |
| `KeyError: 'tool_calls'` or `TypeError: 'NoneType'` | The model answered on its own, so there was no request. That is what step 5 fixes |
| `Port 8000 is already in use` | A server from an earlier run is still on. Press Ctrl+C in its terminal, or run `kill $(lsof -t -i:8000)` |
| `No tools found` | `@mcp.tool` is missing above your function, or you did not restart the server |
| `fastmcp list` on the deployed address asks you to sign in | Add `--auth none` to the command, and check Authentication is off on the Gateway page |

Notes for this lecture: https://100x-curriculum.vercel.app/c8/module-2/lecture-12-building-with-tool-calling-and-mcp/notes
