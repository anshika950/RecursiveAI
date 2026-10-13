"""Token counting for AI-generated text.

Uses tiktoken's cl100k_base encoding (the same family of BPE tokenizer used
by modern OpenAI/GPT-style models) to produce a real sub-word token count,
instead of a naive whitespace word count. Falls back to the word count if
the encoding can't be loaded (e.g. a transient network blip on first use) so
a tokenizer hiccup never turns into a 500 for the caller.
"""

_encoding = None
_encoding_load_failed = False


def _get_encoding():
    global _encoding, _encoding_load_failed
    if _encoding is not None or _encoding_load_failed:
        return _encoding
    try:
        import tiktoken

        _encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        _encoding_load_failed = True
        _encoding = None
    return _encoding


def count_tokens(text: str) -> int:
    encoding = _get_encoding()
    if encoding is None:
        return len(text.split())
    try:
        return len(encoding.encode(text))
    except Exception:
        return len(text.split())
