"""Model providers and the owner's cloud opt-in. Keys live only in the encrypted vault (providers table).

LiteLLM learns them through a generated config + a 0600 env file in PAI_SHARED_DIR; the YAML only holds
`os.environ/PAI_KEY_<NAME>` references. Changes take effect after `docker compose restart litellm`.
"""
import os
import re
import shlex
import tempfile
import time
from contextlib import closing

import yaml

from pai import blocks
from pai.routing import Route

PROVIDERS = {"openrouter": "openrouter/", "huggingface": "huggingface/", "nvidia": "nvidia_nim/",
             "ollama": "ollama/", "lmstudio": "lm_studio/"}
CLOUD = ("openrouter", "nvidia", "huggingface")  # also the order pai-cloud picks the first configured one
LOCAL_BACKENDS = ("ollama", "lmstudio")  # external local servers: no key, optional base URL in settings
# UNVERIFIED defaults: model ids were not checked against the providers' catalogues. Editable via PUT /api/providers.
DEFAULT_MODELS = {
    "openrouter": "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "nvidia": "nvidia_nim/meta/llama-3.3-70b-instruct",
    "huggingface": "huggingface/meta-llama/Llama-3.3-70B-Instruct",
}
CLOUD_SYSTEM = "You are PAI, a private assistant. Be brief and concrete."
WARNING = "Cloud models see what you send. Free tiers may log prompts. Names and secrets are blocked or kept on this box."
_BASE_YAML = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "litellm.local.yaml"),
              os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "litellm.local.yaml")]


def _db():
    import main  # late import: main owns the vault path, and imports this module
    return main.db()


def _setting(con, key: str, default: str | None = None) -> str | None:
    row = con.execute("select value from settings where key = ?", (key,)).fetchone()
    return row[0] if row else default


def get_setting(key: str, default: str | None = None) -> str | None:
    with closing(_db()) as con:
        return _setting(con, key, default)


def set_setting(key: str, value: str) -> None:
    with closing(_db()) as con, con:
        con.execute("insert into settings (key, value) values (?, ?) on conflict(key) do update set value = excluded.value", (key, value))


def _upsert(name: str, **cols) -> None:
    if name not in PROVIDERS:
        raise KeyError(name)
    with closing(_db()) as con, con:
        con.execute("insert or ignore into providers (name, updated) values (?, ?)", (name, time.time()))
        for c, v in cols.items():  # column names come from this module, never from callers' input
            con.execute(f"update providers set {c} = ?, updated = ? where name = ?", (v, time.time(), name))


def save_key(name: str, key: str) -> None:
    _upsert(name, key=key or None)  # empty key removes it


def save_model(name: str, model: str) -> None:
    _upsert(name, model=model or None)


def set_cloud_enabled(on: bool) -> None:
    set_setting("cloud_enabled", "1" if on else "0")


def cloud_enabled() -> bool:
    return get_setting("cloud_enabled") == "1"


def rows() -> dict[str, dict]:
    with closing(_db()) as con:
        return {n: {"key": k, "model": m} for n, k, m in con.execute("select name, key, model from providers")}


def cloud_provider() -> str | None:
    r = rows()
    return next((n for n in CLOUD if r.get(n, {}).get("key")), None)


def off_limits() -> list[str]:
    with closing(_db()) as con:
        row = con.execute("select value from profile where key = 'off_limits'").fetchone()
    return [p.strip() for p in re.split(r"[,;\n]", row[0]) if p.strip()] if row else []


def cloud_decision(text: str, want_cloud: bool) -> tuple[str, str]:
    """(model, reason): reason says why a requested cloud call stayed local, '' when not applicable."""
    if not want_cloud:
        return "pai-chat", ""
    if not cloud_enabled() or not cloud_provider():
        return "pai-chat", "cloud is not set up"
    ok, why = blocks.allowed_for_cloud(text, off_limits())
    return ("pai-cloud", "") if ok else ("pai-chat", why)


def choose_model(text: str, route: Route, want_cloud: bool = False) -> str:
    """Cloud only when the owner asked for it on this request; routing alone never selects it."""
    return cloud_decision(text, want_cloud)[0]


def render_litellm_config() -> str:
    base = next(p for p in _BASE_YAML if os.path.exists(p))
    with open(base) as f:
        cfg = yaml.safe_load(f)
    r = rows()
    first = cloud_provider()
    if first:
        cfg["model_list"].append({"model_name": "pai-cloud", "litellm_params": {
            "model": r[first]["model"] or DEFAULT_MODELS[first], "api_key": f"os.environ/PAI_KEY_{first.upper()}"}})
    for n in LOCAL_BACKENDS:  # only when the owner gave both a base URL and a model
        base_url, model = get_setting(f"{n}_base"), r.get(n, {}).get("model")
        if base_url and model:
            cfg["model_list"].append({"model_name": f"pai-{n}", "litellm_params": {"model": model, "api_base": base_url}})
    return yaml.safe_dump(cfg, sort_keys=False)


KEY_RE = re.compile(r"[\x21-\x7e]{1,512}")  # printable ASCII only: anything else could break the shell that sources the env file


def render_env() -> str:
    out = []
    for n, v in rows().items():
        if n in CLOUD and v["key"]:
            if not KEY_RE.fullmatch(v["key"]):
                raise ValueError(f"stored key for {n} is not printable ASCII")  # never emit something that could brick litellm
            out.append(f"PAI_KEY_{n.upper()}={shlex.quote(v['key'])}\n")
    return "".join(out)


def _write_if_changed(path: str, text: str, mode: int) -> None:
    try:
        with open(path) as f:
            if f.read() == text:
                return
    except FileNotFoundError:
        pass
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def write_files() -> None:
    d = os.environ.get("PAI_SHARED_DIR", "/shared")
    os.makedirs(d, exist_ok=True)
    _write_if_changed(os.path.join(d, "litellm.env"), render_env(), 0o600)
    _write_if_changed(os.path.join(d, "litellm.generated.yaml"), render_litellm_config(), 0o644)
