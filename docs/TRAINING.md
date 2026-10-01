# Training OSAI without another AI API

OSAI's bootstrap neural model is intentionally local and vendor-independent. It does not require API keys.

## 1. Prepare a lawful corpus

Create a UTF-8 text file containing source code and technical material you are allowed to use. Good categories for an OS-building model include Linux kernel documentation, shell, Python, C, Rust, systemd units, Debian packaging metadata, desktop files, YAML, JSON, GRUB, live-build examples and your own successful OS projects.

Do not blindly scrape copyrighted repositories or include secrets, credentials, private code, malware or destructive scripts.

## 2. Install ML support

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[ml]'
```

## 3. Train the bootstrap model

```bash
python scripts/train_local_model.py ./data/os-code-corpus.txt \
  --out ./models/osai-bootstrap.pt \
  --steps 20000
```

The bootstrap model uses OSAI's own reversible byte tokenizer. This makes it fully independent but less efficient than a large learned tokenizer. For a production-scale model, the next stage should add a tokenizer trained from the same authorized corpus, multi-file datasets, validation splits, checkpoint metadata, distributed training, instruction tuning and code/build execution feedback.

## Reality check

A model does not become an expert programmer merely because a Transformer class exists. High capability comes from dataset quality, parameter count, training compute, evaluation and repeated correction. OSAI therefore keeps its deterministic OS planner and validators usable even when no neural checkpoint exists; the neural model is an enhancement rather than a hidden dependency.
