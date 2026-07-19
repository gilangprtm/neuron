"""Neuron Vector Embeddings — placeholder re-export for API parity.

The real implementation lives in neuron_embed.py (FastEmbed). This module
re-exports the same symbols so callers can `from src.neuron_embed import ...`.
"""

from src.neuron_embed import (  # noqa: F401
    _Embedder,
    cosine_similarity_batch,
    cosine_similarity_single,
    embedding_dim,
    get_embedder,
)
