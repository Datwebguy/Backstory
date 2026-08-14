from pathlib import Path
from backstory.config import Settings
from backstory.demo.load_demo import load
from backstory.demo.scenarios import USER
from backstory.engine.memory import MemoryEngine
from backstory.hydra.client import HydraClient

settings = Settings(backstory_data_dir=Path("runs/debug"))
engine = MemoryEngine(settings=settings, hydra=HydraClient(settings))
load(engine, USER)
for q in ["What do I know about Ada?", "Why did I choose the ThinkPad?"]:
    seeds = engine.retriever.seed_entities(q, USER)
    print("Q", q)
    print(" seeds", seeds)
    for sid in seeds:
        print("  seed", sid, engine.hydra.query("MATCH (n {id:$i}) RETURN n.name AS name, n.canonical_key AS k", {"i": sid}).mappings())
    facts = engine.retriever.facts_for_entities(seeds)
    print(" facts", [(f.subject_name, f.predicate, f.object_text, f.is_current) for f in facts])
    from backstory.engine.abstain import decide
    d = decide(q, facts)
    print(" decision", d.action, d.reason, len(d.facts))
engine.close()
