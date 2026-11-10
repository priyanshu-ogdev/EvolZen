"""Phase 0 sanity test for EmbeddingRouter — skips cleanly if the heavy deps aren't installed.

This is the intended pattern for any test touching an optional-extra-adjacent dependency: fail
soft in environments that only ran `uv sync` (base deps), fail loud in CI configurations that
are supposed to have the full stack.
"""
import pytest

pytest.importorskip("faiss")
pytest.importorskip("sentence_transformers")

from evolzen.recognition.embedding_router import EmbeddingRouter  # noqa: E402


def test_route_raises_before_index_is_built() -> None:
    router = EmbeddingRouter()
    with pytest.raises(RuntimeError):
        router.route(query_embedding=[0.0] * 384, top_k=3)
