"""Concrete FAISS + sentence-transformers implementation of `ExpertRouter` (Phase 2.3).

Replaces a protocol-only stub with a real, swappable reference implementation: embed the query
with a `sentence-transformers` model, search a FAISS index built over the same embedding space
for the rule library's entries, return the top-k rule_ids. CPU (`faiss-cpu`, a base dependency)
by default; swap in `faiss-gpu-cu12` (the `gpu` extra) once the library is large enough for CPU
search to be the bottleneck — the swap is a constructor argument, not a code change, since both
present the same `faiss.Index` interface.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import faiss
    from sentence_transformers import SentenceTransformer


class EmbeddingRouter:
    """A concrete `evolzen.recognition.moe_library.ExpertRouter`.

    Phase 0 stub: the constructor signature and the `route` method's control flow are real;
    the actual FAISS index build (from the rule library's current entries) is left for Phase
    2.3, since it depends on how rule entries get turned into embeddable text — a decision
    that belongs with the wake-sleep implementation, not this scaffold.
    """

    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2") -> None:
        self._embedding_model_name = embedding_model_name
        self._model: SentenceTransformer | None = None
        self._index: faiss.Index | None = None
        self._rule_ids: list[str] = []

    def _ensure_model_loaded(self) -> SentenceTransformer:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._embedding_model_name)
        return self._model

    def build_index(self, rule_id_to_text: dict[str, str]) -> None:
        """(Re)build the FAISS index from the current rule library's entries.

        Call this whenever `evolzen.library.rule_library.RuleLibrary` gains a new entry (Phase
        1.5's spawn event) so routing stays in sync with the library.
        """
        import faiss
        import numpy as np

        model = self._ensure_model_loaded()
        self._rule_ids = list(rule_id_to_text.keys())
        embeddings = model.encode(list(rule_id_to_text.values()), normalize_embeddings=True)
        embeddings_arr = np.asarray(embeddings, dtype="float32")
        index = faiss.IndexFlatIP(embeddings_arr.shape[1])  # cosine sim via inner product on normalized vecs
        index.add(embeddings_arr)
        self._index = index

    def route(self, query_embedding: list[float], top_k: int) -> list[str]:
        """Return the rule_ids of the top_k most relevant library entries."""
        import numpy as np

        if self._index is None:
            raise RuntimeError("build_index() must be called before route().")
        query_arr = np.asarray([query_embedding], dtype="float32")
        _, indices = self._index.search(query_arr, top_k)
        return [self._rule_ids[i] for i in indices[0] if 0 <= i < len(self._rule_ids)]

    def embed_query(self, text: str) -> list[float]:
        """Convenience helper: embed raw text with the same model used to build the index."""
        model = self._ensure_model_loaded()
        return list(model.encode(text, normalize_embeddings=True))
