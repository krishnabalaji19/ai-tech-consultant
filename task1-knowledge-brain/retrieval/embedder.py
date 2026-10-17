"""Local embeddings. No paid API."""

from __future__ import annotations

import os

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from ingestion.config import load_embed_settings


class MiniLMEmbedder:
    def __init__(self, model_name: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer

        name = model_name or load_embed_settings().model_name
        self.model_name = name
        # CPU + small batches keeps an 8 GB Mac from swapping.
        self.model = SentenceTransformer(name, device="cpu")

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            batch_size=8,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]
