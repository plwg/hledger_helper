# hledger Helper (hhelper) - A Command-Line Tool for Managing hledger Files

[Github](https://github.com/plwg/hledger_helper)

Welcome to **hledger Helper (hhelper)**, a command-line tool for simplifying and enhancing your experience with [hledger](https://hledger.org/), the plain-text accounting tool. Whether you're managing transactions, cleaning up your journal, fetching commodity prices, or generating recurring transactions, **hhelper** is here to make your life easier.

## 🌟 Features

**hledger Helper** comes packed with powerful features to streamline your accounting workflow:

1. **Mark Transactions as Cleared**
   Easily mark transactions as cleared directly from the command line. No more manual editing of your ledger files!

2. **Clean Up Journal**
   Automatically clean and format your hledger journal file. This includes aligning amounts, removing unnecessary spaces, and ensuring your journal is valid.

3. **Fetch Prices**
   Fetch historical commodity prices using Yahoo Finance and append them to your price file. Perfect for keeping your commodity valuations up to date.

4. **Generate Recurring Transactions**
   Automatically generate recurring transactions based on your predefined rules. Save time by automating repetitive entries.


## 🚀 Getting Started

### Prerequisites
- Python 3.11 or higher
- [hledger](https://hledger.org/) 1.25 or higher
- A valid `config.toml` file in `~/.config/hhelper/` (see [example config](https://github.com/plwg/hledger_helper))

### Installation

```bash
# install uv (package manager):
curl -LsSf https://astral.sh/uv/install.sh | sh

# restart your terminal, or run the following command:
source $HOME/.local/bin/env # or follow instructions

# install hhelper through uv
uv tool install hhelper

# Run the tool
hh
```

## Screenshots

![Main menu](https://raw.githubusercontent.com/plwg/hledger_helper/refs/heads/dev/screenshots/main.png?raw=true)
![Clean up journal](https://raw.githubusercontent.com/plwg/hledger_helper/refs/heads/dev/screenshots/clean.png?raw=true)
![Clearing transaction](https://raw.githubusercontent.com/plwg/hledger_helper/refs/heads/dev/screenshots/clear.png?raw=true)
![Fetching prices](https://raw.githubusercontent.com/plwg/hledger_helper/refs/heads/dev/screenshots/fetch.png?raw=true)
![Generating recurring transaction](https://raw.githubusercontent.com/plwg/hledger_helper/refs/heads/dev/screenshots/gen_recur.png?raw=true)
---

## 🛠️ Usage

Once you've launched **hhelper**, you'll be greeted with a user-friendly menu where you can select from the available options:

1. **Mark Transactions as Cleared**
   Navigate through your uncleared transactions and mark them as cleared with a single keypress.

2. **Clean Up Journal**
   Automatically clean and format your journal file. The tool will ensure your journal is valid before making any changes.

3. **Fetch Prices**
   Fetch historical prices for your commodities and append them to your price file. You can review the fetched prices before saving.

4. **Generate Recurring Transactions**
   Generate recurring transactions based on a period expression. Preview the transactions before appending them to your journal.


### Finding similar names

```bash
hh --similar
```

Lists transaction descriptions and accounts that look like variants of each other: the same apart from case, spacing or punctuation (`Whole Foods`, `whole foods`), or similar (`Whole Food`, `expenses:grocerys`). Accounts are compared with their siblings, so `assets:bank` and `liabilities:bank` are not reported. It reads your ledger and every file it includes, and changes nothing.

Similar means at most one edit apart (two for names longer than 7 characters), ignoring case, spacing and punctuation. Names shorter than 5 characters or containing digits are only reported when they are the same apart from case, spacing and punctuation, since `Rent` and `Tent` or `Invoice 1001` and `Invoice 1002` usually differ on purpose.

### One-time clean-up

hledger itself covers most of a clean-up:

```bash
hledger accounts --unused       # declared accounts with no postings
hledger accounts --undeclared   # used accounts that are not declared, e.g. typos
hledger check accounts          # fails on undeclared accounts; useful to keep it clean
hledger descriptions | sort -f | uniq -Di   # descriptions differing only in case
```

To fix an account name without editing past transactions, add an alias to your header file, e.g. `alias expenses:grocerys = expenses:groceries`. If names come from bank imports, map them in your CSV rules so they stay fixed.

To rename in the files instead, back up first, then for example (GNU sed; on macOS use `gsed`):

```bash
# Rename an account and its subaccounts in postings and account directives
sed -i -E 's/^([[:space:]]+([*!][[:space:]]*)?[([]?)Expenses:Food\b/\1expenses:food/; s/^account Expenses:Food\b/account expenses:food/' *.journal

# Rename descriptions, keeping the date, status, code and comment
sed -i -E 's/^([0-9][^ ]* +([*!] +)?(\([^)]*\) +)?)(whole foods|Whole Food)( *;.*)?$/\1Whole Foods\5/' *.journal

hledger check -f main.journal
```

## ⚙️ Configuration

**hhelper** requires a `config.toml` file located at `~/.config/hhelper/config.toml`. This file should define the paths to your ledger, price, header, and recurring transaction files. Here's an example configuration:

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


### Backups

Before changing a file, **hhelper** saves a timestamped copy in a `.hhelper/backups` folder in your configured `directory`, keeping the 10 most recent copies of each file. Each save first writes the new content to `.hhelper/tmp`; if the save is interrupted, that copy is kept and its path is shown. If your journal directory is a git repository, add `.hhelper/` to its `.gitignore`.


## 🧪 Development

```bash
uv run pytest
```

The tests run without a terminal or network: prompts and Yahoo Finance are replaced with test doubles. Tests that need hledger are skipped when it is not installed.


## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.


## 🙌 Contributing

Contributions are welcomed! If you have ideas for new features, improvements, or bug fixes, please open an issue or submit a pull request. Let's make **hhelper** even better together!


## 💬 Feedback

If you have any questions, suggestions, or just want to say hello, feel free to open an issue or reach out to us. We'd love to hear from you!

---
Happy accounting with **hledger Helper**! 🎉
