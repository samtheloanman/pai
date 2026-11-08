"""Local sentence embeddings (fastembed, ONNX). The model downloads on first use into DATA_DIR/models."""
import os
import threading

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_model = None
_lock = threading.Lock()


def _load():
    global _model
    with _lock:
        if _model is None:
            from fastembed import TextEmbedding  # lazy: import is slow and the app must boot without it
            _model = TextEmbedding(MODEL, cache_dir=os.path.join(os.getenv("DATA_DIR", "/data"), "models"))
        return _model


def embed(text: str) -> list[float]:
    if os.getenv("PAI_EMBED") == "off":  # used by run-e2e.sh so the test never downloads the model
        raise RuntimeError("embedder disabled (PAI_EMBED=off)")
    m = _load()
    with _lock:  # one ONNX session; serialise calls rather than assume it is re-entrant
        return [float(x) for x in next(iter(m.embed([text])))]
