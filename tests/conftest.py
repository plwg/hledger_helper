from __future__ import annotations

import builtins
import contextlib
import shutil
from collections.abc import Callable, Generator

import pytest

requires_hledger = pytest.mark.skipif(
    shutil.which("hledger") is None, reason="hledger is not installed"
)


class _Capability(str):
    # Stands in for blessed's formatting strings: usable as a string, and
    # callable to wrap text (returned unchanged) or to take parameters
    def __call__(self, *args: object) -> str:
        return args[0] if args and isinstance(args[0], str) else ""


class FakeTerminal:
    width = 80
    height = 24

    def __getattr__(self, name: str) -> _Capability:
        return _Capability("")

    @contextlib.contextmanager
    def cbreak(self) -> Generator[None]:
        yield

    hidden_cursor = cbreak

    def inkey(self) -> str:
        return ""


@pytest.fixture
def term() -> FakeTerminal:
    return FakeTerminal()


@pytest.fixture
def answers(monkeypatch: pytest.MonkeyPatch) -> Callable[..., None]:
    # Scripts the replies to input(); running out behaves like Ctrl-D
    def script(*replies: str) -> None:
        remaining = iter(replies)

        def fake_input(prompt: object = "") -> str:
            try:
                return next(remaining)
            except StopIteration:
                raise EOFError from None

        monkeypatch.setattr(builtins, "input", fake_input)

    return script
