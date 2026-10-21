# Week 4 Writeup — Data Explorer MCP Server

## 1. What I built

`server.py` is a FastMCP server that communicates through STDIO and exposes two tools. `search_countries` intentionally returns a small four-field summary so an agent does not receive the entire country record when it only needs to identify a country. `get_country_details` is the second assigned tool and returns the currencies, languages, border codes, and a flag URL for one selected country.

The provided starter used REST Countries v3.1. That API version is now retired, so I updated the request boundary to the current v5 endpoint and preserved the starter's compact search-result shape. I also pinned MCP below version 2 because the current 2.x package renamed the starter's `FastMCP` import.

## 2. MCP registration and transcript

I registered the server in the project settings for Gemini CLI 0.64.0 with:

```bash
gemini mcp add data-explorer .venv/bin/python server.py --scope project
```

Gemini CLI listed `data-explorer` as the project-local STDIO server. I then connected an MCP client session to the exact same `.venv/bin/python server.py` command, listed its tools, and called both tools. The transcript below contains the MCP responses returned by the running server:

```text
Client: list_tools()
Result: search_countries, get_country_details

Client: search_countries({"query": "Canada", "limit": 1})
Result: {"name": "Canada", "capital": "Ottawa", "region": "Americas", "population": 41798407}

Client: get_country_details({"name": "Canada"})
Result: {"name": "Canada", "currencies": [{"code": "CAD", "name": "Canadian dollar", "symbol": "$"}], "languages": [{"code": "eng", "name": "English"}, {"code": "fra", "name": "French"}], "borders": ["USA"], "flag_url": "https://flags.restcountries.com/v5/w640/ca.png"}
```

## 3. Error handling and verification

Every expected failure crosses the tool boundary as a structured object containing an `error` message and a stable `code`, rather than a Python exception. Empty queries and invalid limits are rejected before a network request. The network layer recognizes 404, authentication, permission, rate-limit, timeout, general HTTP, malformed JSON, and connection failures. A detail lookup returns `not_found` when the API has no result and returns `ambiguous` with candidates when a partial name has multiple possible countries.

I added offline pytest checks so error handling can be verified without consuming an API quota. The tests cover the compact search result, the detail output, invalid input without a request, timeouts, no matches, ambiguous results, and an HTTP 429 response. Running `python -m pytest -q` completed with all tests passing.

## 4. What I learned

This assignment helped me understand why MCP tools should only return the information an agent needs for the current step. The search tool gives a short overview first, and the details tool gives more information after a country has been chosen. I also learned that error handling is important because a clear message helps the agent understand what to try next instead of receiving a confusing crash. Updating the retired API showed me that outside services can change, so it is useful to make the connection between a tool and an API reliable and easy to troubleshoot. Keeping the tool responses focused also makes it easier for the agent to give the user a clear answer without unnecessary information.
