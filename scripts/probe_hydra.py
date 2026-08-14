from backstory.hydra.client import HydraClient, HydraError
from backstory.hydra import schema as S

c = HydraClient()
print("ready", c.ready())

try:
    result = c.write("CREATE (a {id: 910001})-[:FOLLOWS]->(b {id: 910002})")
    print("create_path OK", result.raw)
except HydraError as exc:
    print("create_path ERR", exc.status, exc.body)

for name, fn in [
    (
        "delete",
        lambda: c.write(
            "UNWIND $vertices AS row MATCH (n {id: row.vertex}) DETACH DELETE n",
            {"vertices": [{"vertex": 900001}]},
        ),
    ),
    (
        "upsert",
        lambda: c.write(
            S.UPSERT_ENTITY,
            {"rows": [{"vertex": 900001, "canonical_key": "t:a", "name": "A", "entity_type": "person"}]},
        ),
    ),
    (
        "match",
        lambda: c.query("MATCH (e:Entity {id: $id}) RETURN e.name AS name", {"id": 900001}),
    ),
]:
    try:
        result = fn()
        print(name, "OK", result.rows, result.raw.get("bookmark"))
    except HydraError as exc:
        print(name, "ERR", exc.status, exc.body)

c.close()
