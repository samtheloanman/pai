import pytest

from pai import blocks


@pytest.mark.parametrize("text", [
    "my card is 4111 1111 1111 1111", "4111-1111-1111-1111", "4111111111111111", "amex 378282246310005",
])
def test_card_blocks(text):
    ok, why = blocks.allowed_for_cloud(text, [])
    assert not ok and why == "card number"
    assert "4111" not in why


@pytest.mark.parametrize("text", [
    "sk-abcdefghijklmnopqrstuvwx", "sk-or-v1-abcdefghijklmnopqrstuvwx", "ghp_abcdefghijklmnopqrstuvwxyz0123",
    "AKIAIOSFODNN7EXAMPLE", "xoxb-1234567890-abcdefghij", "xoxp-1234567890-abcdefghij",
    "nvapi-abcdefghijklmnopqrstuvwx", "hf_abcdefghijklmnopqrstuvwx", "token 0123456789abcdef0123456789abcdef",
    "Zm9vYmFyMTIzNDU2Nzg5MGFiY2RlZmdoaWprbG1ub3A=",
])
def test_secret_blocks(text):
    ok, why = blocks.allowed_for_cloud(f"use this: {text} thanks", [])
    assert not ok and why == "secret or key"


def test_ssn_blocks():
    ok, why = blocks.allowed_for_cloud("ssn 123-45-6789", [])
    assert not ok and why == "ID number"


def test_off_limits_whole_phrase_case_insensitive():
    ok, why = blocks.allowed_for_cloud("Tell me about my DIVORCE", ["divorce"])
    assert not ok and why == "off-limits topic" and "divorce" not in why
    assert blocks.allowed_for_cloud("my divorced friend", ["divorce"])[0]
    assert blocks.allowed_for_cloud("my medical records", ["medical records"])[0] is False


@pytest.mark.parametrize("text", [
    "4111 1111 1111 1112",           # 16 digits, fails Luhn
    "deadbeef", "skip the meeting", "sk-short", "call 415 555 1234 today",
    "the quick brown fox", "order 12345-67 shipped",
])
def test_near_misses_pass(text):
    assert blocks.allowed_for_cloud(text, []) == (True, "")


def test_empty_off_limits_entries_ignored():
    assert blocks.allowed_for_cloud("hello", ["", "  "]) == (True, "")
