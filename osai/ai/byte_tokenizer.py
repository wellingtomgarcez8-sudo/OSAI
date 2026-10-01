from __future__ import annotations


class ByteTokenizer:
    """Reversible UTF-8 byte tokenizer used by the bootstrap OSAI model.

    IDs 0..255 map directly to bytes. 256 is BOS and 257 is EOS. Keeping the
    bootstrap tokenizer simple means OSAI can train without importing a
    tokenizer or vocabulary from another AI vendor.
    """

    BOS = 256
    EOS = 257
    vocab_size = 258

    def encode(self, text: str, add_special: bool = True) -> list[int]:
        ids = list(text.encode("utf-8"))
        return [self.BOS, *ids, self.EOS] if add_special else ids

    def decode(self, ids: list[int]) -> str:
        data = bytes(i for i in ids if 0 <= i <= 255)
        return data.decode("utf-8", errors="replace")
