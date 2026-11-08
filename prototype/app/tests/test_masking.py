from pai.masking import Masker


def test_masks_email_phone_and_names_and_restores():
    m = Masker(["Zed Quill"])
    out = m.mask("Mail bob@example.com or call 415 555 1234. I am zed, Quill is my surname.")
    assert "bob@example.com" not in out and "415" not in out and "zed" not in out.lower() and "quill" not in out.lower()
    assert m.count == 4
    assert m.unmask(out.replace("Mail", "Re:")) == "Re: bob@example.com or call 415 555 1234. I am zed, Quill is my surname."


def test_same_value_same_placeholder_across_messages():
    m = Masker([])
    a, b = m.mask("bob@example.com"), m.mask("again bob@example.com")
    assert a in b and m.count == 1


def test_nothing_to_mask_is_unchanged():
    m = Masker(["Zed"])
    assert m.mask("what is the weather") == "what is the weather" and m.count == 0
    assert m.unmask("sunny") == "sunny"


def test_name_matches_whole_words_only():
    m = Masker(["Al"])
    assert m.mask("Alaska and al") == "Alaska and [NAME_1]"
