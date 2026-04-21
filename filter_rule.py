"""Keyword filter: '장내매수' / '증여'. Matches after whitespace squash."""
from __future__ import annotations

KEYWORDS = ("장내매수", "증여")


def match(text: str) -> list[str]:
    squashed = "".join(text.split())
    return [k for k in KEYWORDS if k in squashed]


if __name__ == "__main__":
    assert match("본문에 장내매수 발생") == ["장내매수"]
    assert match("장 내 매수 방식") == ["장내매수"], "whitespace variant must match"
    assert match("증여에 의한 취득") == ["증여"]
    assert match("취득 처분 합계") == []
    assert set(match("장내매수와 증여 동시")) == {"장내매수", "증여"}
    print("filter_rule self-test OK")
