# Data Explorer MCP Server

This is a small [Model Context Protocol](https://modelcontextprotocol.io) server that lets an MCP-aware client look up country information through the [REST Countries API](https://restcountries.com/). It provides two focused tools over **STDIO**, rather than a web server.

| Tool | Purpose |
| --- | --- |
| `search_countries(query, limit=5)` | Find compact summaries for matching countries. |
| `get_country_details(name)` | Get currencies, languages, borders, and a flag URL. |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` pins the MCP package below version 2 because this project uses the
FastMCP 1.x API included with the course starter.

Optional developer test dependencies:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

## Run locally

```bash
python server.py
```

The process communicates using MCP over standard input and output. It will appear to wait for input when started directly, which is expected.

## Register with an MCP client

Add this entry to your MCP client's configuration, replacing the two paths with the absolute paths on your computer:

```json
{
  "mcpServers": {
    "data-explorer": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/server.py"]
    }
  }
}
```

For example, in Gemini CLI, add the same command as a local STDIO MCP server in its settings, restart the CLI, and verify that `data-explorer` appears in the available tools. If using a personal REST Countries key, add it to the server's environment configuration rather than committing it to this repository.

For this project, the registration command was:

```bash
gemini mcp add data-explorer .venv/bin/python server.py --scope project
```

To use a free personal API key on macOS/Linux, set it only in your shell environment before launching your MCP client:

```bash
export RESTCOUNTRIES_API_KEY="your-key-here"
```

## Tools

### `search_countries(query, limit=5)`

Searches countries by name and returns each match's common name, capital, region, and population. `limit` is an integer from 1 through 20, it defaults to 5. An empty list means no result matched.

Example prompt: “Use `search_countries` to find countries matching `united` and show the first 3.”

### `get_country_details(name)`

Returns a matching country's currencies, languages, border codes, and a flag image URL. Currency and language values keep both a human-readable name and the available code. If a partial name has several matches, the result includes candidate names instead of choosing one silently.

Example prompt: “Use `get_country_details` to give me details about Canada.”

## Error handling

Both tools validate input and return structured error objects rather than raising exceptions. `search_countries` keeps its list contract by returning errors as a one-item list. `get_country_details` returns an error object directly.

| Code | Meaning |
| --- | --- |
| `invalid_input` | A name was empty or the limit was outside 1–20. |
| `not_found` | The detail lookup found no matching country. |
| `ambiguous` | A detail lookup matched multiple countries; use a supplied candidate. |
| `timeout` / `network_error` | The upstream service was slow or unavailable. |
| `auth_failed`, `forbidden`, `rate_limited` | REST Countries rejected, refused, or throttled the request. |
| `upstream_error` / `bad_response` | The service returned an unexpected HTTP response or JSON shape. |

## Project layout

```text
server.py                 # FastMCP server and two tools
requirements.txt          # runtime dependencies
requirements-dev.txt      # optional pytest dependency
tests/test_server.py      # offline tool and error-handling tests
writeup.md                # transcript and reflection
```
