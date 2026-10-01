from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ModelConfig:
    vocab_size: int = 258
    context_length: int = 512
    hidden_size: int = 384
    layers: int = 6
    heads: int = 6


class LocalCodeModel:
    """Optional local decoder-only Transformer loaded only from local weights."""

    def __init__(self, weights: Path | None = None, config: ModelConfig | None = None):
        self.weights = weights
        self.config = config or ModelConfig()
        self.model: Any | None = None

    @property
    def available(self) -> bool:
        return self.weights is not None and self.weights.exists()

    def load(self) -> None:
        if not self.available:
            raise FileNotFoundError("local OSAI model weights were not found")
        import torch
        import torch.nn as nn

        cfg = self.config

        class Block(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.norm1 = nn.LayerNorm(cfg.hidden_size)
                self.attn = nn.MultiheadAttention(cfg.hidden_size, cfg.heads, batch_first=True)
                self.norm2 = nn.LayerNorm(cfg.hidden_size)
                self.mlp = nn.Sequential(
                    nn.Linear(cfg.hidden_size, cfg.hidden_size * 4),
                    nn.GELU(),
                    nn.Linear(cfg.hidden_size * 4, cfg.hidden_size),
                )

            def forward(self, x):
                n = self.norm1(x)
                seq = n.size(1)
                mask = torch.triu(torch.full((seq, seq), float("-inf"), device=x.device), diagonal=1)
                a, _ = self.attn(n, n, n, attn_mask=mask, need_weights=False)
                x = x + a
                return x + self.mlp(self.norm2(x))

        class Decoder(nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.token = nn.Embedding(cfg.vocab_size, cfg.hidden_size)
                self.pos = nn.Embedding(cfg.context_length, cfg.hidden_size)
                self.blocks = nn.ModuleList([Block() for _ in range(cfg.layers)])
                self.norm = nn.LayerNorm(cfg.hidden_size)
                self.head = nn.Linear(cfg.hidden_size, cfg.vocab_size, bias=False)
                self.head.weight = self.token.weight

            def forward(self, ids):
                ids = ids[:, -cfg.context_length :]
                positions = torch.arange(ids.size(1), device=ids.device)
                x = self.token(ids) + self.pos(positions)[None, :, :]
                for block in self.blocks:
                    x = block(x)
                return self.head(self.norm(x))

        model = Decoder()
        payload = torch.load(self.weights, map_location="cpu", weights_only=True)
        model.load_state_dict(payload)
        model.eval()
        self.model = model

    def logits(self, token_ids: list[int]):
        if self.model is None:
            self.load()
        import torch

        ids = torch.tensor([token_ids], dtype=torch.long)
        with torch.inference_mode():
            return self.model(ids)[:, -1, :]
