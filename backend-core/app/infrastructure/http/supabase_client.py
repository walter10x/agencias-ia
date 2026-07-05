"""Minimal Supabase REST client using httpx directly.

Talks to PostgREST API without supabase-py key validation.
Avoids circular imports by being a standalone module.
"""

from __future__ import annotations


class SupabaseHttpClient:
    """Minimal Supabase REST client using httpx directly."""

    def __init__(self, url: str, key: str) -> None:
        self.url = url.rstrip("/")
        self.key = key
        self._headers = {
            "Content-Type": "application/json",
        }

    def table(self, name: str) -> _TableQuery:
        return _TableQuery(self, name)


class _TableQuery:
    """Fluent query builder mimicking supabase-py API."""

    def __init__(self, client: SupabaseHttpClient, table: str) -> None:
        self._client = client
        self._table = table
        self._method = "GET"
        self._params: dict = {}
        # Filtros de columna acumulados como pares (columna, operador.valor).
        # Lista (no dict) para permitir dos filtros sobre la misma columna,
        # ej. starts_at=gte.X & starts_at=lte.Y
        self._filter_params: list[tuple[str, str]] = []
        self._body: dict | list | None = None
        self._headers: dict = {}
        self._url_path: str = table

    def select(self, *columns: str) -> _TableQuery:
        cols = ",".join(columns) if columns else "*"
        self._headers["Prefer"] = "return=representation"
        self._params["select"] = cols
        return self

    def insert(self, data: dict | list) -> _TableQuery:
        self._method = "POST"
        self._headers["Prefer"] = "return=representation"
        self._body = data
        return self

    def upsert(self, data: dict, on_conflict: str = "id") -> _TableQuery:
        self._method = "POST"
        self._headers["Prefer"] = "return=representation,resolution=merge-duplicates"
        self._body = data
        self._params["on_conflict"] = on_conflict
        return self

    def update(self, data: dict) -> _TableQuery:
        self._method = "PATCH"
        self._headers["Prefer"] = "return=representation"
        self._body = data
        return self

    def delete(self) -> _TableQuery:
        self._method = "DELETE"
        self._headers["Prefer"] = "return=representation"
        return self

    def eq(self, column: str, value: str | bool | int) -> _TableQuery:
        self._filter_params.append((column, f"eq.{value}"))
        return self

    def neq(self, column: str, value: str) -> _TableQuery:
        self._filter_params.append((column, f"neq.{value}"))
        return self

    def gt(self, column: str, value: str | int) -> _TableQuery:
        self._filter_params.append((column, f"gt.{value}"))
        return self

    def gte(self, column: str, value: str | int) -> _TableQuery:
        self._filter_params.append((column, f"gte.{value}"))
        return self

    def lt(self, column: str, value: str | int) -> _TableQuery:
        self._filter_params.append((column, f"lt.{value}"))
        return self

    def lte(self, column: str, value: str | int) -> _TableQuery:
        self._filter_params.append((column, f"lte.{value}"))
        return self

    def in_(self, column: str, values: list[str]) -> _TableQuery:
        joined = ",".join(str(v) for v in values)
        self._filter_params.append((column, f"in.({joined})"))
        return self

    def is_(self, column: str, value: str) -> _TableQuery:
        """Filtro PostgREST `is` — para comparar contra NULL/true/false.

        PostgREST exige el operador `is` (no `eq`) para NULL: `eq.null`
        no es válido. Uso: `.is_("reminder_sent_at", "null")`.
        """
        self._filter_params.append((column, f"is.{value}"))
        return self

    def order(self, column: str, *, desc: bool = False, nullsfirst: bool = False) -> _TableQuery:
        direction = f"{column}.desc" if desc else column
        if nullsfirst:
            direction += ".nullsfirst"
        self._params["order"] = direction
        return self

    def limit(self, n: int) -> _TableQuery:
        self._params["limit"] = str(n)
        return self

    def offset(self, n: int) -> _TableQuery:
        self._params["offset"] = str(n)
        return self

    def execute(self) -> _QueryResult:
        """Execute the query synchronously and return a result object."""
        import json
        import urllib.parse

        import httpx

        url = f"{self._client.url}/rest/v1/{self._url_path}"
        qs_parts = []
        for k, v in self._params.items():
            qs_parts.append(f"{k}={urllib.parse.quote(str(v))}")
        for k, v in self._filter_params:
            qs_parts.append(f"{k}={urllib.parse.quote(str(v))}")
        if qs_parts:
            url += "?" + "&".join(qs_parts)

        headers = {**self._client._headers, **self._headers}
        body_str = None
        if self._body is not None:
            body_str = json.dumps(self._body)

        try:
            response = httpx.request(
                method=self._method,
                url=url,
                headers=headers,
                content=body_str,
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json() if response.content else []
            if not isinstance(data, list):
                data = [data]
            return _QueryResult(data=data, count=len(data))
        except httpx.HTTPStatusError as exc:
            err_body = exc.response.text if exc.response else ""
            raise RuntimeError(f"Supabase error: {err_body}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Supabase connection failed: {exc}") from exc


class _QueryResult:
    """Minimal result object mimicking supabase-py response."""

    def __init__(self, data: list, count: int) -> None:
        self.data = data
        self.count = count
