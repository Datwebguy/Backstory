from pathlib import Path

from backstory.engine.normalize import canonical_key
from backstory.engine.resolve import EntityResolver
from backstory.sidecar.store import SidecarStore


def test_exact_and_alias_not_fuzzy(tmp_path: Path):
    store = SidecarStore(tmp_path / "side.sqlite")
    resolver = EntityResolver(store)
    sam = resolver.resolve("Sam", "person", aliases=["@sam"])
    again = resolver.resolve("@sam", "person")
    assert again.entity_id == sam.entity_id
    samuel = resolver.resolve("Samuel", "person")
    assert samuel.entity_id != sam.entity_id
    manager = resolver.resolve("my old manager", "person")
    assert manager.entity_id not in {sam.entity_id, samuel.entity_id}
    linked = resolver.resolve("Samuel from Acme", "person", aliases=["Samuel"])
    assert linked.entity_id == samuel.entity_id
    assert canonical_key("Sam", "person") == "person:sam"
