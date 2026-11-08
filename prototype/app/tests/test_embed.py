import pytest


def test_embed_off_raises_and_skips_model(monkeypatch):
    monkeypatch.undo()  # drop the autouse fake so the real function runs
    from pai import embed
    monkeypatch.setenv("PAI_EMBED", "off")
    monkeypatch.setattr(embed, "_load", lambda: pytest.fail("model must not load"))
    with pytest.raises(RuntimeError, match="PAI_EMBED=off"):
        embed.embed("hi")
