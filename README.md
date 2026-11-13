# hledger Helper (hhelper)

A terminal menu for routine chores on [hledger](https://hledger.org/) journals.

- **Mark Transactions as Cleared**: step through uncleared transactions, optionally filtered by regex, and clear them one keypress at a time.
- **Clean Up Journal**: rewrite the journal through `hledger print`, sorted and aligned, after checking the result reads the same as before.
- **Fetch Prices**: download daily prices from Yahoo Finance and merge them into your price file.
- **Generate Recurring Transactions**: preview the transactions your periodic rules produce for a period, then append them to the journal.

## Install

Requires Python 3.11+ and hledger 1.52+ (CI tests 1.52.4 and the 2.0 pre-release 1.99.5).

```bash
uv tool install hhelper
hh
```

No uv yet? `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Usage

| Command | Does |
|---|---|
| `hh` | Open the menu |
| `hh --similar` | List descriptions and accounts that look like variants of each other (e.g. `Whole Foods` / `Whole Food`) and how to fix them; changes nothing |
| `hh --clean-up` | Clean up the journal without asking; exits 1 if nothing was written |
| `hh --fetch-prices` | Fetch prices and write them without asking; exits 1 if none were fetched |
| `hh --config` | Print the config file's location and content |
| `hh --version` | Print the version |

## Configuration

`~/.config/hhelper/config.toml`:

```toml
[paths]
directory = "~/finance"
ledger_file = "journal.ledger"
price_file = "prices.ledger"
header_file = "header.ledger"
recurring_tx_file = "recurring.ledger"

[commodities]
commodity_pairs = [
    { symbol = "AAPL", base_currency = "USD", quote_currency = "AAPL", is_append_space = true },
    { symbol = "BTC-USD", base_currency = "USD", quote_currency = "BTC", is_append_space = false },
]
```

Clean Up Journal drops directives and comments, so keep them in the header file, which the cleaned journal includes.

## Backups

Before changing a file, hhelper copies it to `.hhelper/backups/` in your `directory`, keeping the 10 most recent copies per file. Add `.hhelper/` to `.gitignore` if your journal is in git.

## Development

```bash
uv run pytest
```

Tests need no terminal or network; those needing hledger are skipped if it is not installed.

## License

MIT, see [LICENSE](LICENSE). Issues and pull requests welcome.
