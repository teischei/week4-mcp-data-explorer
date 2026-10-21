# offline checks for the tool contracts and the error boundary.
import httpx
import server


CANADA = {
    "names": {"common": "Canada"},
    "capitals": [{"name": "Ottawa"}],
    "region": "Americas",
    "population": 41798407,
    "currencies": [{"code": "CAD", "name": "Canadian dollar", "symbol": "$"}],
    "languages": [{"iso639_3": "eng", "name": "English"}],
    "borders": ["USA"],
    "flag": {"url_png": "https://example.test/ca.png"},
}


def api_response(objects, status=200):
    request = httpx.Request("GET", "https://api.restcountries.com/countries/v5")
    return httpx.Response(status, json={"data": {"objects": objects}}, request=request)


def test_search_returns_the_compact_starter_shape(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *args, **kwargs: api_response([CANADA]))

    assert server.search_countries("Canada") == [{
        "name": "Canada",
        "capital": "Ottawa",
        "region": "Americas",
        "population": 41798407,
    }]


def test_details_returns_the_requested_fields(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *args, **kwargs: api_response([CANADA]))

    assert server.get_country_details("Canada") == {
        "name": "Canada",
        "currencies": [{"code": "CAD", "name": "Canadian dollar", "symbol": "$"}],
        "languages": [{"code": "eng", "name": "English"}],
        "borders": ["USA"],
        "flag_url": "https://example.test/ca.png",
    }


def test_invalid_input_never_calls_the_network(monkeypatch):
    def should_not_run(*args, **kwargs):
        raise AssertionError("unexpected request")

    monkeypatch.setattr(server.httpx, "get", should_not_run)

    assert server.search_countries("   ") == [{
        "error": "query must not be empty", "code": "invalid_input"
    }]
    assert server.search_countries("Canada", 0) == [{
        "error": "limit must be a whole number from 1 to 20", "code": "invalid_input"
    }]


def test_timeout_becomes_a_structured_result(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(httpx.TimeoutException("slow")))

    assert server.get_country_details("Canada") == {
        "error": "the country data service timed out; please try again", "code": "timeout"
    }


def test_no_result_and_ambiguous_result_are_explained(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *args, **kwargs: api_response([]))
    assert server.get_country_details("Atlantis") == {
        "error": "no country found matching 'Atlantis'", "code": "not_found"
    }

    matches = [{"names": {"common": "Congo"}}, {"names": {"common": "Congo (Kinshasa)"}}]
    monkeypatch.setattr(server.httpx, "get", lambda *args, **kwargs: api_response(matches))
    result = server.get_country_details("Republic of Congo")
    assert result["code"] == "ambiguous"
    assert result["candidates"] == ["Congo", "Congo (Kinshasa)"]


def test_http_failures_keep_a_status_code(monkeypatch):
    monkeypatch.setattr(server.httpx, "get", lambda *args, **kwargs: api_response([], status=429))

    assert server.search_countries("Canada") == [{
        "error": "REST Countries rate limit reached; wait and retry",
        "code": "rate_limited",
        "status": 429,
    }]
