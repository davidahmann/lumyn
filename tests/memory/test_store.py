import shutil
from pathlib import Path

from lumyn.memory.client import MemoryStore
from lumyn.memory.types import Experience

DB_PATH = Path(".lumyn/test_memory")


def setup_module() -> None:
    if DB_PATH.exists():
        shutil.rmtree(DB_PATH)


def teardown_module() -> None:
    if DB_PATH.exists():
        shutil.rmtree(DB_PATH)


def test_add_and_search() -> None:
    store = MemoryStore(db_path=DB_PATH)

    # Create dummy vector (dim=384 for realism with default model, but logic is agnostic)
    # Using small dim for test speed if possible, but LanceDB handles it.
    vec = [0.1] * 384

    exp = Experience(
        decision_id="dec_01",
        vector=vec,
        outcome=-1,  # Failure
        severity=5,
        original_verdict="ALLOW",
        timestamp="2023-10-01T12:00:00Z",
    )

    store.add_experiences([exp])

    # Search with same vector
    hits = store.search(vec, limit=1)

    assert len(hits) == 1
    hit = hits[0]
    assert hit.experience.decision_id == "dec_01"
    assert hit.experience.outcome == -1
    assert hit.experience.severity == 5
    # Similarity should be close to 1.0
    assert hits[0].score > 0.99


def test_persistence() -> None:
    # Verify data persists across instances
    store = MemoryStore(db_path=DB_PATH)
    hits = store.search([0.1] * 384, limit=1)
    assert len(hits) == 1
    assert hits[0].experience.decision_id == "dec_01"
