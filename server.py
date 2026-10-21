"""Data Explorer — an STDIO MCP server for Week 4.

Wraps the REST Countries API and exposes concise country data to an agent through two
tools. All expected failures are returned as structured results instead of exceptions.

Setup:
    pip install -r requirements.txt
Run (STDIO) — register this command in your MCP client (e.g. Claude Desktop / an IDE):
    python server.py
"""
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# v5 accepts a documented demo key for setup, a personal key enables query-specific live results.
BASE_URL = "https://api.restcountries.com/countries/v5"
DEMO_KEY = "rc_live_demo"
mcp = FastMCP("data-explorer")

TIMEOUT_SECONDS = 10
MAX_RESULTS = 20


def _error(code: str, message: str, **extra: Any) -> dict[str, Any]:
    # return errors in a predictable, MCP-friendly shape.
    return {"error": message, "code": code, **extra}


def _api_key() -> str:
    # read a personal key at call time, or use REST Countries' public demo mode.
    return os.environ.get("RESTCOUNTRIES_API_KEY", "").strip() or DEMO_KEY


def _common_name(country: dict[str, Any]) -> str | None:
    names = country.get("names")
    return names.get("common") if isinstance(names, dict) else None


def _capital(country: dict[str, Any]) -> str | None:
    capitals = country.get("capitals")
    if not isinstance(capitals, list):
        return None
    first = next((capital for capital in capitals if isinstance(capital, dict)), None)
    return first.get("name") if first else None


def _lookup_country(name: str, limit: int = 10) -> list[dict[str, Any]] | dict[str, Any]:
    # fetch countries by name while keeping network failures out of tool callers.
    if not isinstance(name, str) or not name.strip():
        return _error("invalid_input", "country name must not be empty")

    try:
        response = httpx.get(
            BASE_URL,
            params={"q": name.strip(), "limit": limit},
            headers={"Authorization": f"Bearer {_api_key()}"},
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        if response.status_code == 404:
            return []
        if response.status_code == 401:
            return _error("auth_failed", "REST Countries rejected the API key", status=401)
        if response.status_code == 403:
            return _error("forbidden", "REST Countries refused the request", status=403)
        if response.status_code == 429:
            return _error("rate_limited", "REST Countries rate limit reached; wait and retry", status=429)
        if response.status_code >= 400:
            return _error(
                "upstream_error",
                f"REST Countries returned HTTP {response.status_code}",
                status=response.status_code,
            )
        payload = response.json()
    except httpx.TimeoutException:
        return _error("timeout", "the country data service timed out; please try again")
    except httpx.HTTPError:
        return _error("network_error", "the country data service could not be reached; please try again")
    except ValueError:
        return _error("bad_response", "the country data service returned an invalid response")

    objects = payload.get("data", {}).get("objects") if isinstance(payload, dict) else None
    if not isinstance(objects, list):
        return _error("bad_response", "the country data service returned an unexpected response")
    return objects


@mcp.tool()
def search_countries(query: str, limit: int = 5) -> list[dict[str, Any]]:
    # search countries by name. returns a list of {name, capital, region, population}.
    # an empty result means no country matched. Errors are returned as one-item lists
    # containing an object with `error` and `code` fields.
    if not isinstance(query, str) or not query.strip():
        return [_error("invalid_input", "query must not be empty")]
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= MAX_RESULTS:
        return [_error("invalid_input", f"limit must be a whole number from 1 to {MAX_RESULTS}")]

    countries = _lookup_country(query, limit)
    if isinstance(countries, dict):
        return [countries]

    results = []
    for c in countries[: min(limit, MAX_RESULTS)]:
        results.append(
            {
                "name": _common_name(c),
                "capital": _capital(c),
                "region": c.get("region"),
                "population": c.get("population"),
            }
        )
    return results


@mcp.tool()
def get_country_details(name: str) -> dict[str, Any]:
    # get currencies, languages, bordering country codes, and a flag URL for one country.
    # if a partial name has several matches, returns candidate names instead of guessing.
    countries = _lookup_country(name)
    if isinstance(countries, dict):
        return countries
    if not countries:
        return _error("not_found", f"no country found matching '{name.strip()}'")

    exact = next((country for country in countries if (_common_name(country) or "").casefold() == name.strip().casefold()), None)
    if exact is not None:
        country = exact
    elif len(countries) > 1:
        candidates = [_common_name(country) for country in countries]
        return _error(
            "ambiguous",
            f"'{name.strip()}' matched several countries; use a more specific name",
            candidates=[candidate for candidate in candidates if candidate],
        )
    else:
        country = countries[0]

    currencies = country.get("currencies") if isinstance(country.get("currencies"), list) else []
    languages = country.get("languages") if isinstance(country.get("languages"), list) else []
    flag = country.get("flag") if isinstance(country.get("flag"), dict) else {}

    return {
        "name": _common_name(country),
        "currencies": [
            {"code": currency.get("code"), "name": currency.get("name"), "symbol": currency.get("symbol")}
            for currency in currencies if isinstance(currency, dict)
        ],
        "languages": [
            {"code": language.get("iso639_3") or language.get("iso639_1"), "name": language.get("name")}
            for language in languages if isinstance(language, dict)
        ],
        "borders": country.get("borders") if isinstance(country.get("borders"), list) else [],
        "flag_url": flag.get("url_png") or flag.get("url_svg"),
    }


if __name__ == "__main__":
    mcp.run()
