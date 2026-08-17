"""HydraDB OSS HTTP client.

Talks to graph-node exactly as documented in the official README and
implemented in src/client/http.rs:

  POST /v1/graphs/{graph_id}/query
  Authorization: Bearer <token>
  X-Graph-Namespace: <namespace>
  {"cell_id","query","parameters","consistency","bookmark","query_id"}

`query_id` doubles as the durable write deduplication key. It is
optional in the wire format, but omitting it is unsafe: graph-node then
derives one from a process local counter (`http-query-{n}` in
src/client/http.rs), which restarts at zero on every process restart.
Against a persistent object store those keys are still on record from
the previous process, so a restarted node reuses `http-query-14` for a
different edge and the write fails with

  idempotency key conflict for create request key
  http-query-14.unwind-create-matched...: this key already stored a
  result for a different edge

which surfaces to callers as a plain 500. This client therefore always
sends a unique `query_id`.

A listening port is not proof. Callers must assert on returned rows.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

from backstory.config import Settings, get_settings


class HydraError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list[Any]]
    bookmark: str | None
    read_epoch: int | None
    query_id: str | None
    raw: dict[str, Any] = field(default_factory=dict)

    def scalars(self, column: str | None = None) -> list[Any]:
        if not self.rows:
            return []
        if column is None:
            return [row[0] if row else None for row in self.rows]
        idx = self.columns.index(column)
        return [row[idx] for row in self.rows]

    def first_scalar(self) -> Any:
        if not self.rows or not self.rows[0]:
            return None
        return self.rows[0][0]

    def mappings(self) -> list[dict[str, Any]]:
        return [dict(zip(self.columns, row, strict=False)) for row in self.rows]


def unwrap_value(cell: Any) -> Any:
    if not isinstance(cell, dict) or "type" not in cell:
        return cell
    kind = cell.get("type")
    value = cell.get("value")
    if kind in {"vertex_id", "integer", "signed_integer", "float", "boolean", "string", "null"}:
        return value
    if kind == "list":
        return [unwrap_value(item) for item in (value or [])]
    if kind == "path":
        return value
    return value


class HydraClient:
    def __init__(self, settings: Settings | None = None, *, timeout: float = 30.0):
        self.settings = settings or get_settings()
        self._timeout = timeout
        self._bookmark: str | None = None
        self._http = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> HydraClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @property
    def last_bookmark(self) -> str | None:
        return self._bookmark

    def ready(self) -> bool:
        try:
            response = self._http.get(f"{self.settings.hydra_admin_url.rstrip('/')}/readyz")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    def health(self) -> dict[str, Any]:
        response = self._http.get(f"{self.settings.hydra_http_url.rstrip('/')}/healthz")
        response.raise_for_status()
        return response.json()

    def query(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
        *,
        consistency: str = "causal",
        bookmark: str | None = None,
        use_last_bookmark: bool = True,
    ) -> QueryResult:
        token = self.settings.hydra_token
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Graph-Namespace": self.settings.hydra_namespace,
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "cell_id": self.settings.hydra_cell_id,
            "query": cypher,
            "parameters": parameters or {},
            "consistency": consistency,
            # Unique per request. See the module docstring: letting
            # graph-node generate this from its restart-local counter
            # causes idempotency conflicts against a persistent store.
            "query_id": f"backstory-{uuid.uuid4()}",
        }
        chosen = bookmark
        if chosen is None and use_last_bookmark:
            chosen = self._bookmark
        if chosen:
            body["bookmark"] = chosen
        url = (
            f"{self.settings.hydra_http_url.rstrip('/')}"
            f"/v1/graphs/{self.settings.hydra_graph_id}/query"
        )
        try:
            response = self._http.post(url, headers=headers, json=body)
        except httpx.HTTPError as exc:
            raise HydraError(f"HydraDB HTTP transport failed: {exc}") from exc
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {"text": response.text}
            raise HydraError(
                f"HydraDB query failed ({response.status_code}): {payload}",
                status=response.status_code,
                body=payload,
            )
        payload = response.json()
        rows = [[unwrap_value(cell) for cell in row] for row in payload.get("rows", [])]
        result = QueryResult(
            columns=list(payload.get("columns") or []),
            rows=rows,
            bookmark=payload.get("bookmark"),
            read_epoch=payload.get("read_epoch"),
            query_id=payload.get("query_id"),
            raw=payload,
        )
        if result.bookmark:
            self._bookmark = result.bookmark
        return result

    def write(self, cypher: str, parameters: dict[str, Any] | None = None) -> QueryResult:
        """Mutation helper. Returns the bookmark of the committed write."""
        return self.query(cypher, parameters, consistency="causal")
