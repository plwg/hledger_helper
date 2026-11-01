from __future__ import annotations

import base64
import http.client
import json
import threading
from typing import TYPE_CHECKING, Any

import pytest

from hhelper.web.csv_import import (
    RulesPathError,
    find_rules_files,
    match_rules,
    preview_csv,
    resolve_rules_path,
)
from hhelper.web.server import Api, ApiError, make_server
from tests.conftest import requires_hledger

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

# Made-up bank export and rules; no real account data
CSV = (
    "Date,Description,Withdrawals,Deposits\n"
    "21/02/2025,COFFEE SHOP  TOWN,3.50,\n"
    "22/02/2025,MYSTERY STORE,12.00,\n"
)

RULES = """skip 1
fields date, description, amount-out, amount-in
date-format %d/%m/%Y
currency $
account1 assets:bank

if COFFEE
  description Coffee
  account2 expenses:coffee
"""


@pytest.fixture
def rules_dir(tmp_path: Path) -> Path:
    (tmp_path / "card").mkdir()
    (tmp_path / "card" / "card.csv.rules").write_text(RULES)
    (tmp_path / "savings.rules").write_text(RULES)
    (tmp_path / ".hhelper").mkdir()
    (tmp_path / ".hhelper" / "old.rules").write_text(RULES)
    return tmp_path


def test_find_rules_files_skips_hidden_folders(rules_dir: Path) -> None:
    assert find_rules_files(rules_dir) == ["card/card.csv.rules", "savings.rules"]


def test_find_rules_files_missing_folder(tmp_path: Path) -> None:
    assert find_rules_files(tmp_path / "nope") == []


@pytest.mark.parametrize(
    ("csv_name", "expected"),
    [
        ("card.csv", "card/card.csv.rules"),
        ("card (2).csv", "card/card.csv.rules"),
        ("Savings_2025-02.CSV", "savings.rules"),
        ("statement.csv", None),
    ],
)
def test_match_rules(csv_name: str, expected: str | None) -> None:
    rules = ["card/card.csv.rules", "savings.rules"]
    assert match_rules(csv_name, rules).path == expected


def test_match_rules_prefers_longest_contained_name() -> None:
    rules = ["main.csv.rules", "a/main_bonus.csv.rules"]
    assert match_rules("main_bonus_jan.csv", rules).path == "a/main_bonus.csv.rules"


def test_match_rules_by_folder_words() -> None:
    rules = ["checking_bank_a/main.rules", "card_bank_b/main.rules"]
    assert match_rules("bank_b export.csv", rules).path == "card_bank_b/main.rules"


@pytest.mark.parametrize(
    "relative",
    ["../x.rules", "/etc/x.rules", "a/../../x.rules", ".hidden/x.rules", "x.txt", ""],
)
def test_resolve_rules_path_rejects_outside_paths(
    rules_dir: Path, relative: str
) -> None:
    with pytest.raises(RulesPathError):
        resolve_rules_path(rules_dir, relative)


def test_resolve_rules_path_rejects_symlink_out(
    rules_dir: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    outside = tmp_path_factory.mktemp("outside") / "outside.rules"
    outside.write_text(RULES)
    (rules_dir / "link.rules").symlink_to(outside)
    with pytest.raises(RulesPathError):
        resolve_rules_path(rules_dir, "link.rules")


@requires_hledger
def test_preview_csv_flags_unknown(rules_dir: Path) -> None:
    preview = preview_csv(
        CSV.encode(), "card.csv", rules_dir / "card" / "card.csv.rules", None
    )

    assert preview.error == ""
    assert "expenses:coffee" in preview.journal
    assert [(t.description, t.unknown) for t in preview.transactions] == [
        ("Coffee", False),
        ("MYSTERY STORE", True),
    ]
    assert preview.transactions[0].postings[0].amount == "-$3.50"


@requires_hledger
def test_preview_csv_with_unsaved_rules(rules_dir: Path) -> None:
    rules = RULES + "\nif MYSTERY\n  account2 expenses:misc\n"
    preview = preview_csv(
        CSV.encode(), "odd name.txt", rules_dir / "savings.rules", rules
    )

    assert preview.error == ""
    assert not any(t.unknown for t in preview.transactions)


@requires_hledger
def test_preview_csv_reports_hledger_error(rules_dir: Path) -> None:
    preview = preview_csv(
        b"not,a\nbank,file\n", "x.csv", rules_dir / "savings.rules", None
    )

    assert preview.error
    assert preview.transactions == []


def test_save_rules_backs_up_and_checks_mtime(rules_dir: Path) -> None:
    api = Api(rules_dir)
    loaded = api.read_rules("savings.rules")
    # Sent as text, as a browser cannot hold nanoseconds in a number exactly
    assert isinstance(loaded["mtime"], str)

    saved = api.save_rules(
        {"path": "savings.rules", "content": "skip 2\n", "mtime": loaded["mtime"]}
    )

    assert (rules_dir / "savings.rules").read_text() == "skip 2\n"
    assert list((rules_dir / ".hhelper" / "backups").iterdir())
    assert api.read_rules("savings.rules")["mtime"] == saved["mtime"]

    with pytest.raises(ApiError, match="changed on disk"):
        api.save_rules({"path": "savings.rules", "content": "x", "mtime": "1"})


def test_save_rules_creates_new_file(rules_dir: Path) -> None:
    api = Api(rules_dir)
    api.save_rules({"path": "new/bank.csv.rules", "content": RULES, "mtime": None})

    assert (rules_dir / "new" / "bank.csv.rules").read_text() == RULES
    with pytest.raises(ApiError, match="already exists"):
        api.save_rules({"path": "new/bank.csv.rules", "content": "", "mtime": None})


@pytest.fixture
def server(rules_dir: Path) -> Generator[int]:
    httpd = make_server(rules_dir, 0)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()


def request(
    port: int,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
    all_headers = {"Content-Type": "application/json", **(headers or {})}
    payload = json.dumps(body) if body is not None else None
    connection.request(method, path, payload, all_headers)
    response = connection.getresponse()
    data = response.read()
    connection.close()
    if response.getheader("Content-Type", "").startswith("application/json"):
        return response.status, json.loads(data)
    return response.status, data.decode()


def test_server_serves_page_and_lists_rules(server: int) -> None:
    status, page = request(server, "GET", "/")
    assert status == 200
    assert "<title>hhelper CSV Import</title>" in page

    status, data = request(server, "GET", "/api/rules")
    assert data["rules"] == ["card/card.csv.rules", "savings.rules"]

    status, data = request(server, "GET", "/api/match?name=card.csv")
    assert data["path"] == "card/card.csv.rules"


def test_server_refuses_other_sites(server: int) -> None:
    status, _ = request(
        server, "GET", "/api/rules", headers={"Origin": "https://evil.example"}
    )
    assert status == 403

    status, _ = request(server, "GET", "/api/rules", headers={"Host": "evil.example"})
    assert status == 403


def test_server_refuses_path_traversal(server: int) -> None:
    status, data = request(server, "GET", "/api/rules/file?path=../../etc/passwd")
    assert status == 400
    assert "error" in data


@requires_hledger
def test_server_preview(server: int) -> None:
    body = {
        "csv_name": "card.csv",
        "csv_base64": base64.b64encode(CSV.encode()).decode(),
        "rules": "card/card.csv.rules",
    }
    status, data = request(server, "POST", "/api/preview", body)

    assert status == 200
    assert len(data["transactions"]) == 2
