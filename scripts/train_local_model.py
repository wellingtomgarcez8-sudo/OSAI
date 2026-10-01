#!/usr/bin/env python3
from __future__ import annotations

import argparse
import random
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the bootstrap OSAI model locally")
    parser.add_argument("corpus", type=Path, help="UTF-8 text/code corpus")
    parser.add_argument("--out", type=Path, default=Path("models/osai-bootstrap.pt"))
    parser.add_argument("--steps", type=int, default=2000)
    parser.add_argument("--context", type=int, default=512)
    parser.add_argument("--hidden", type=int, default=384)
    parser.add_argument("--layers", type=int, default=6)
    parser.add_argument("--heads", type=int, default=6)
    parser.add_argument("--lr", type=float, default=3e-4)
    args = parser.parse_args()

    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    from osai.ai.byte_tokenizer import ByteTokenizer

    tokenizer = ByteTokenizer()
    data = tokenizer.encode(args.corpus.read_text(encoding="utf-8", errors="replace"))
    if len(data) <= args.context + 1:
        raise SystemExit("corpus is smaller than the selected context window")

    class Block(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.n1 = nn.LayerNorm(args.hidden)
            self.attn = nn.MultiheadAttention(args.hidden, args.heads, batch_first=True)
            self.n2 = nn.LayerNorm(args.hidden)
            self.ff = nn.Sequential(
                nn.Linear(args.hidden, args.hidden * 4),
                nn.GELU(),
                nn.Linear(args.hidden * 4, args.hidden),
            )

        def forward(self, x):
            n = self.n1(x)
            s = n.size(1)
            mask = torch.triu(torch.full((s, s), float("-inf"), device=x.device), diagonal=1)
            a, _ = self.attn(n, n, n, attn_mask=mask, need_weights=False)
            x = x + a
            return x + self.ff(self.n2(x))

    class Model(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.tok = nn.Embedding(tokenizer.vocab_size, args.hidden)
            self.pos = nn.Embedding(args.context, args.hidden)
            self.blocks = nn.ModuleList([Block() for _ in range(args.layers)])
            self.norm = nn.LayerNorm(args.hidden)
            self.head = nn.Linear(args.hidden, tokenizer.vocab_size, bias=False)
            self.head.weight = self.tok.weight

        def forward(self, ids):
            positions = torch.arange(ids.size(1), device=ids.device)
            x = self.tok(ids) + self.pos(positions)[None, :, :]
            for block in self.blocks:
                x = block(x)
            return self.head(self.norm(x))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = Model().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    for step in range(1, args.steps + 1):
        start = random.randint(0, len(data) - args.context - 2)
        chunk = data[start : start + args.context + 1]
        x = torch.tensor([chunk[:-1]], dtype=torch.long, device=device)
        y = torch.tensor([chunk[1:]], dtype=torch.long, device=device)
        logits = model(x)
        loss = F.cross_entropy(logits.reshape(-1, tokenizer.vocab_size), y.reshape(-1))
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if step == 1 or step % 50 == 0:
            print(f"step={step} loss={loss.item():.4f} device={device}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    state = {k: v.detach().cpu() for k, v in model.state_dict().items()}
    torch.save(state, args.out)
    print(f"saved: {args.out}")


if __name__ == "__main__":
    main()
