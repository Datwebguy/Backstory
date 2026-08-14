"""Live HydraDB capability + persistence smoke.

Must pass before any memory extraction is trusted. Does not use Postgres.
"""

from __future__ import annotations

import argparse
import sys
import time

from backstory.hydra.client import HydraClient, HydraError
from backstory.hydra import schema as S


def wait_ready(client: HydraClient, timeout: float = 120.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if client.ready():
            return
        time.sleep(1.5)
    raise SystemExit("HydraDB /readyz did not become ready. Is docker compose up?")


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run_capability_matrix(client: HydraClient) -> dict[str, str]:
    results: dict[str, str] = {}

    def check(name: str, fn) -> None:
        try:
            fn()
            results[name] = "PASS"
            print(f"PASS  {name}")
        except Exception as exc:  # noqa: BLE001
            results[name] = f"FAIL: {exc}"
            print(f"FAIL  {name}: {exc}")

    A, B, C, D, E = 900001, 900002, 900003, 900004, 900005
    client.write(
        "UNWIND $vertices AS row MATCH (n {id: row.vertex}) DETACH DELETE n",
        {"vertices": [{"vertex": v} for v in (A, B, C, D, E, 900010, 900011)]},
    )

    def fact_row(vertex: int, city: str, current: bool, stated: str, until: str, status: str, digest: str) -> dict:
        return {
            "vertex": vertex,
            "predicate": "lives_in",
            "object_text": city,
            "fact_kind": "state",
            "predicate_class": "unique_state",
            "stated_at": stated,
            "valid_from": stated,
            "valid_until": until,
            "event_at": "",
            "is_current": current,
            "confidence": 0.9,
            "status": status,
            "polarity": 1,
            "qualifiers": "",
            "speaker": "user",
            "atom_hash": digest,
        }

    def nodes() -> None:
        client.write(
            S.UPSERT_ENTITY,
            {
                "rows": [
                    {"vertex": A, "canonical_key": "smoke:ada", "name": "Ada", "entity_type": "person"},
                    {"vertex": B, "canonical_key": "smoke:lagos", "name": "Lagos", "entity_type": "place"},
                    {"vertex": C, "canonical_key": "smoke:abuja", "name": "Abuja", "entity_type": "place"},
                ]
            },
        )
        client.write(
            S.UPSERT_FACT,
            {
                "rows": [
                    fact_row(D, "Lagos", False, "2023-02-01T10:00:00", "2023-06-01T10:00:00", "superseded", "smoke-lagos"),
                    fact_row(E, "Abuja", True, "2023-06-01T10:00:00", "", "active", "smoke-abuja"),
                ]
            },
        )

    def relationships() -> None:
        client.write(S.create_rel_query(S.ABOUT), {"rows": [
            {"source_vertex": D, "destination_vertex": A},
            {"source_vertex": E, "destination_vertex": A},
        ]})
        client.write(S.create_rel_query(S.OBJECT_ENTITY), {"rows": [
            {"source_vertex": D, "destination_vertex": B},
            {"source_vertex": E, "destination_vertex": C},
        ]})
        client.write(S.create_rel_query(S.SUPERSEDES), {"rows": [
            {"source_vertex": E, "destination_vertex": D},
        ]})

    def query_current() -> None:
        result = client.query(
            """
            MATCH (f:Fact)-[:ABOUT]->(e:Entity {id: $entity_id})
            WHERE f.predicate = $predicate AND f.is_current = true
            RETURN f.object_text AS city
            """,
            {"entity_id": A, "predicate": "lives_in"},
        )
        expect(result.first_scalar() == "Abuja", f"current city was {result.rows}")

    def query_history() -> None:
        result = client.query(
            """
            MATCH (cur:Fact {id: $fid})-[:SUPERSEDES*1..4]->(old:Fact)
            RETURN old.object_text AS city
            """,
            {"fid": E},
        )
        expect(result.first_scalar() == "Lagos", f"history was {result.rows}")

    def query_multihop() -> None:
        result = client.query(
            """
            MATCH (old:Fact {id: $fid})-[:ABOUT]->(e:Entity)
            MATCH (cur:Fact)-[:ABOUT]->(e)
            WHERE cur.is_current = true
            RETURN cur.object_text AS city
            """,
            {"fid": D},
        )
        expect(result.first_scalar() == "Abuja", f"multihop was {result.rows}")

    def query_string_time() -> None:
        result = client.query(
            """
            MATCH (f:Fact)-[:ABOUT]->(e:Entity {id: $entity_id})
            WHERE f.predicate = $predicate AND f.valid_from <= $as_of AND (f.valid_until = $open OR f.valid_until >= $as_of)
            RETURN f.object_text AS city
            """,
            {
                "entity_id": A,
                "predicate": "lives_in",
                "as_of": "2023-03-15T00:00:00",
                "open": "",
            },
        )
        expect(result.first_scalar() == "Lagos", f"as-of March was {result.rows}")

    def reject_is_null() -> None:
        try:
            client.query("MATCH (f:Fact) WHERE f.valid_until IS NULL RETURN f.id AS id")
        except HydraError as exc:
            expect(exc.status == 400, f"unexpected error for IS NULL: {exc}")
            return
        raise AssertionError("HydraDB accepted IS NULL; schema assumption is wrong")

    def reject_undirected() -> None:
        try:
            client.query("MATCH (a:Entity)-[:ABOUT]-(b) RETURN a.id AS id")
        except HydraError:
            return
        raise AssertionError("HydraDB accepted an undirected pattern")

    def contradicts() -> None:
        x, y = 900010, 900011
        client.write(
            S.UPSERT_FACT,
            {
                "rows": [
                    fact_row(x, "Lagos", True, "2023-07-01T00:00:00", "", "contradicted", "c1"),
                    fact_row(y, "Abuja", True, "2023-07-02T00:00:00", "", "contradicted", "c2"),
                ]
            },
        )
        client.write(
            S.create_rel_query(S.CONTRADICTS),
            {
                "rows": [
                    {"source_vertex": x, "destination_vertex": y},
                    {"source_vertex": y, "destination_vertex": x},
                ]
            },
        )
        result = client.query(
            """
            MATCH (f:Fact {id: $fid})-[:CONTRADICTS]->(g:Fact)
            RETURN g.object_text AS city
            """,
            {"fid": x},
        )
        expect(result.first_scalar() == "Abuja", f"contradicts was {result.rows}")

    def bounded_varlength() -> None:
        result = client.query(
            "MATCH (cur:Fact {id: $fid})-[:SUPERSEDES*1..3]->(old:Fact) RETURN count(*) AS n",
            {"fid": E},
        )
        expect(result.first_scalar() == 1, f"varlength count {result.rows}")

    check("upsert_and_label", nodes)
    check("create_relationships", relationships)
    check("current_state_filter", query_current)
    check("supersedes_history", query_history)
    check("two_hop_about", query_multihop)
    check("iso_string_as_of", query_string_time)
    check("is_null_rejected", reject_is_null)
    check("undirected_rejected", reject_undirected)
    check("contradicts_both_directions", contradicts)
    check("bounded_variable_length", bounded_varlength)
    return results


def run_persistence_check(client: HydraClient) -> None:
    result = client.query(
        """
        MATCH (f:Fact)-[:ABOUT]->(e:Entity {id: $entity_id})
        WHERE f.predicate = $predicate AND f.is_current = true
        RETURN f.object_text AS city
        """,
        {"entity_id": 900001, "predicate": "lives_in"},
    )
    expect(result.first_scalar() == "Abuja", f"persistence check failed: {result.rows}")
    print("PASS  persistence_after_reconnect")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HydraDB smoke + schema capability matrix")
    parser.add_argument("--skip-wait", action="store_true")
    parser.add_argument("--persist-only", action="store_true")
    args = parser.parse_args(argv)
    with HydraClient() as client:
        if not args.skip_wait:
            print("Waiting for HydraDB /readyz ...")
            wait_ready(client)
            print("HydraDB is ready.")
        if args.persist_only:
            run_persistence_check(client)
            return 0
        results = run_capability_matrix(client)
        failed = [name for name, status in results.items() if not status.startswith("PASS")]
        if failed:
            print("SMOKE FAILED:", ", ".join(failed))
            return 1
        print("SMOKE OK")
        return 0


if __name__ == "__main__":
    sys.exit(main())
