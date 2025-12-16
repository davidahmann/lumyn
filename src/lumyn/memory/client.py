from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import lancedb  # type: ignore

from lumyn.memory.types import Experience, MemoryHit

# LanceDB uses fixed schemas. We let Pydantic model it or define it.
# Actually lancedb python client can verify schema from data.


class MemoryStore:
    def __init__(self, db_path: str | Path = ".lumyn/memory") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(self.db_path)

        # Ensure table exists
        self.table_name = "experiences"

    def add_experiences(self, experiences: Sequence[Experience]) -> None:
        if not experiences:
            return

        data = [
            {
                "decision_id": e.decision_id,
                "vector": e.vector,
                "outcome": e.outcome,
                "severity": e.severity,
                "original_verdict": e.original_verdict,
                "timestamp": e.timestamp,
            }
            for e in experiences
        ]

        if self.table_name in self.db.table_names():
            tbl = self.db.open_table(self.table_name)
            tbl.add(data)
        else:
            self.db.create_table(self.table_name, data=data)

    def search(self, query_vector: list[float], limit: int = 5) -> list[MemoryHit]:
        if self.table_name not in self.db.table_names():
            return []

        tbl = self.db.open_table(self.table_name)

        # LanceDB search
        # metric="cosine" is default for vector search usually?
        # fastembed vectors are normalized? BGE usually are.
        # Assuming normalized vectors, dot product == cosine similarity.

        results_df = tbl.search(query_vector).limit(limit).to_pandas()

        hits = []
        for _, row in results_df.iterrows():
            # Calculate similarity? LanceDB returns distance usually.
            # _distance column
            dist = row.get("_distance", 1.0)
            # If using l2, sim = 1 / (1+dist)?
            # If using cosine distance, sim = 1 - dist.
            similarity = 1.0 - dist

            exp = Experience(
                decision_id=row["decision_id"],
                vector=row["vector"],  # Might come back as array
                outcome=int(row["outcome"]),
                severity=int(row["severity"]),
                original_verdict=row["original_verdict"],
                timestamp=row["timestamp"],
            )
            similarity = 1.0 - dist
            hits.append(MemoryHit(experience=exp, score=similarity))

        return hits
