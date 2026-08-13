# BIP-39 256-bit Mnemonic Generator

> **A complete, dependency-free, audited implementation of BIP-39**
> **with a 256-bit entropy target (24-word mnemonic).**
>
> Offline-first · Auditable · For humans — beginners included.

**Languages:** [English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

**Runtime i18n:** the CLI/interactive mode auto-detects your language
from the `LANG` / `LC_ALL` / `BIP39_LANG` environment variables and
prints prompts in English, 简体中文, or 日本語 accordingly.  Any other
locale falls back to English.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-BIP--39%20vectors%20passing-brightgreen.svg)](docs/BIP39-math.md)
[![BIP-39](https://img.shields.io/badge/BIP--39-spec%20vectors%20verified-blueviolet.svg)](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki)

---

## Why this project exists

In **July 2026**, the Bitcoin community was hit by the
[**Coldcard random-number-generator vulnerability**](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/) — a single
buggy conditional branch in the firmware released in **March 2021**
that caused wallet seeds to be generated with **~40 bits of effective
entropy instead of 128** on the Mk3, and ~72 bits on the Mk4/Mk5/Q.
At least **15 attackers** drained roughly **1,367 BTC (~$88–111 M)**
from ~7,300 addresses in four coordinated waves on July 30–31, 2026.
A Reddit developer later reproduced the bug in **8 minutes** using
Claude Code — the flaw had been hiding in plain sight on GitHub for
five years.

The incident refuted three myths at once:

1. *"Hardware wallets are secure by construction."* — No. The seed is
   software, and software has bugs.
2. *"Open-source firmware is safer."* — In principle, yes. In practice,
   this bug survived five years of community review.
3. *"Just upgrade the firmware."* — It does not work. The patch fixes
   *future* generation, but every seed already produced by the broken
   RNG is still broken. The only cure is to **generate a new seed and
   migrate the funds**.

The deeper lesson is that **no vendor — no matter how reputable —
can take responsibility for the entropy that protects your money**. The
only trust assumption you can fully verify yourself is the randomness
source itself.

This project is the answer to that lesson. It is the smallest,
*auditable* code that:

1. **Generates a full 256-bit, 24-word BIP-39 mnemonic** from any entropy
   source you trust: dice, coins, a shuffled deck, a CSV file you
   filled in by hand.
2. **Runs 8 NIST SP 800-22 statistical tests** on your entropy and
   refuses to produce a weak mnemonic.
3. **Validates** any existing 24-word mnemonic and shows you the
   corresponding 512-bit BIP-39 seed.
4. **Has zero runtime dependencies** beyond the Python standard library,
   so you can run it on a fully air-gapped computer.
5. **Reads nothing from disk and writes nothing to disk** in its
   interactive mode — the entropy lives only in process memory and
   is wiped when you close the terminal.

Read the full story in [`BACKGROUND.md`](BACKGROUND.md). Every line
fits on one screen. Every step is documented.

---

## Features

| | |
|---|---|
| Spec | [BIP-39](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki) — full 256-bit entropy / 24 words / 8-bit checksum |
| Algorithm | SHA-256 checksum + 24 × 11-bit lookup into the official 2048-word English list |
| Seed derivation | PBKDF2-HMAC-SHA512, 2048 iterations, 64-byte output (matches Trezor, Ledger, MetaMask, etc.) |
| Entropy inputs | dice rolls · coin flips · shuffled card deck · CSV/TXT hand-entered bits |
| Network usage | **None.** No HTTP, no telemetry, no temp-file leaks. |
| Dependencies | Python ≥ 3.7 standard library only (the optional `numbers-parser` is *only* needed for `.numbers` files) |
| Tests | 12 unit tests, including 4 official BIP-39 vectors with `TREZOR` passphrase |

---

## TL;DR — generate a mnemonic in 30 seconds

```bash
# 1. Clone (or download the zip) onto an OFFLINE computer.
git clone https://github.com/qianmyth/bip39-256bit-entropy-mnemonic.git
cd bip39-256bit-entropy-mnemonic

# 2. Run the demo CSV (entropy = 0; this produces the famous
#    "abandon × 23, art" sentence and is useful for verifying the tool).
python3 bip39_offline_v5.py generate examples/demo_zero_entropy.csv

# 3. Print the famous "abandon…art" sentence, run the test suite.
python3 -m unittest discover -s tests -v
```

Once you trust the toolchain, copy `templates/blank_template.csv` into a
spreadsheet app, fill it in with your real entropy, and run:

```bash
python3 bip39_offline_v5.py generate my_entropy.csv
```

The output shows you every intermediate value (24 binary groups → 256-bit
entropy → SHA-256 checksum → 264 bits → 11-bit segments → 24 words). You can
visually verify each step.

---

## Repository layout

```
bip39-256bit-entropy-mnemonic/
├── README.md                  ← you are here (English)
├── README.zh-CN.md            ← 简体中文
├── README.ja.md               ← 日本語
├── README.ko.md               ← 한국어
├── HOWTO-dice.md              ← step-by-step "roll 99 dice" guide (4 langs)
├── BACKGROUND.md              ← why this exists, post-mortem of past leaks
├── SECURITY.md                ← threat model & best practices
├── LICENSE                    ← MIT
├── english.txt                ← official BIP-39 2048-word list
├── bip39_offline_v5.py        ← the single-file implementation
├── examples/
│   ├── demo_zero_entropy.csv  ← produces "abandon…art"
│   └── example_full.csv       ← a non-zero sample
├── templates/
│   └── blank_template.csv     ← start here when collecting entropy
└── docs/
    └── BIP39-math.md          ← visual walk-through of the algorithm
```

---

## Installation

You don't need to install anything. Just clone and run.

```bash
git clone https://github.com/qianmyth/bip39-256bit-entropy-mnemonic.git
cd bip39-256bit-entropy-mnemonic
python3 -m unittest discover -s tests    # optional: verify the tool works
```

Required: **Python 3.7+** (uses `hashlib.pbkdf2_hmac`). Tested on macOS, Linux,
Windows.

If you want to read a macOS Numbers file directly:

```bash
pip install numbers-parser    # do this ONCE on an internet-connected machine
                              # then move the script to your offline computer
```

---

## Usage

### 1. From dice rolls — most secure human-only source

See `HOWTO-dice.md` for the full procedure (English + 3 translations). Quick
version:

```bash
# Roll a fair d6 100 times, write the results one per line in rolls.txt:
#   4
#   6
#   1
#   3
#   ...

python3 bip39_offline_v5.py from-dice rolls.txt
```

The script will print the 32-byte entropy and the resulting 24-word mnemonic.

### 2. From a CSV / TXT hand-filled table

```
templates/blank_template.csv          ← 24 rows × 11 columns of 0/1
```

Mark each cell with a `1` if a coin came up heads, a `0` for tails, or use
dice by taking `1 = odd, 0 = even`. Fill the file in on a computer that has
*never* been online, then run:

```bash
python3 bip39_offline_v5.py generate blank_template.csv
```

### 3. Validate an existing 24-word mnemonic

```bash
python3 bip39_offline_v5.py validate \
    "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art"
# → checksum: VALID ✓

python3 bip39_offline_v5.py validate --show-seed --passphrase TREZOR \
    "abandon abandon abandon ... art"
# → entropy (hex): 0000…0000
# → seed (BIP-39, passphrase='TREZOR'): bda8…cc8
```

### 4. Use as a Python library

```python
import bip39_offline_v5 as bip39

# 256 bits of entropy (e.g. from os.urandom or dice)
entropy = bip39.dice_rolls_to_entropy([3, 5, 6, 1, 2, ...])   # 100+ rolls

# Mnemonic
mnemonic = bip39.entropy_to_mnemonic(entropy)
print(" ".join(mnemonic))

# Validate
assert bip39.validate_mnemonic(mnemonic)

# Seed (what a wallet would import)
seed = bip39.mnemonic_to_seed(mnemonic, passphrase="optional-BIP39-passphrase")
# 64 bytes, ready for BIP-32 HD-key derivation
```

---

## What the tool actually does (math)

BIP-39 for 256 bits is six small steps:

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 256 random bits  →  SHA-256 → take first 8 bits  =  8-bit checksum    │
 │                                                                        │
 │ (256 bits) ++ (8 bits)  =  264 bits                                    │
 │                                                                        │
 │ split into 24 groups of 11 bits each  →  24 indices 0…2047             │
 │                                                                        │
 │ index → english.txt[index]   =   24 words                              │
 └────────────────────────────────────────────────────────────────────────┘
```

See `docs/BIP39-math.md` for a colour-coded walkthrough with worked examples
(using the all-zeros entropy → “abandon × 23, art”).

---

## Verification

The script `bip39_offline_v5.py` validates its own implementation
**at run time** by re-deriving the BIP-39 zero-entropy vector
(`abandon × 23, art`).  You can sanity-check the rest manually:

```bash
# 1. Zero entropy → canonical "abandon × 23, art" mnemonic
python3 bip39_offline_v5.py generate examples/demo_zero_entropy.csv

# 2. Validate any 24-word mnemonic
python3 bip39_offline_v5.py validate \
    "abandon abandon abandon abandon abandon abandon abandon abandon \
     abandon abandon abandon abandon abandon abandon abandon abandon \
     abandon abandon abandon abandon abandon abandon abandon art"

# 3. Derive the BIP-39 seed (should match the official Trezor test vector)
python3 bip39_offline_v5.py validate --show-seed --passphrase TREZOR \
    <above 24 words>

# 4. Audit any 256-bit entropy source against the NIST battery
python3 bip39_offline_v5.py check-entropy my_entropy.csv
```

Expected output for step 3:

```
checksum: VALID
entropy (hex): 0000000000000000000000000000000000000000000000000000000000000000
seed (BIP-39, passphrase='TREZOR'): bda85446c68413707090a52022edd26a
    1c9462295029f2e60cd7c4f2bbd3097170af7a4d73245cafa9c3cca8d561a7c3
    de6f5d4a10be8ed2a5e608d68f92fcc8
```

If those check out, the BIP-39 algorithm is correct to the byte.

---

## Security — read this before generating real money

1. **Run on an air-gapped computer.** Even if the code is clean, keyloggers,
   screen-capture malware and supply-chain attacks on the OS can leak your
   mnemonic. Recommended: a brand-new live-USB Linux boot (e.g. Tails) on a
   machine that has never touched the internet.
2. **Verify the checksum is correct** — the script prints it explicitly.
   Compare it to any second independent implementation (e.g. the
   [`iancoleman/bip39`](https://github.com/iancoleman/bip39) web tool,
   running offline).
3. **Add a BIP-39 passphrase** (the optional 25th “word”). Without it, anyone
   who finds your 24 words owns your coins. With it, even *you* cannot
   recover your coins if you forget it. Store it separately.
4. **Cross-check with two different entropy sources** (e.g. dice *and*
   coin flips) when handling large balances.
5. **Never type a real mnemonic on an internet-connected device.** The
   `--show-seed` flag exists for testing only — treat its output as
   radioactive once it carries real entropy.

Full threat model in `SECURITY.md`.

---

## Why we only ship 256-bit (24 words)?

The shorter BIP-39 variants (12 / 15 / 18 / 21 words) are still spec-compliant,
but every modern hardware wallet defaults to 24 words. The test vectors, the
demo CSV, the templates and the dice threshold (99 fair rolls) are all tuned
for the 256-bit case. Adding the shorter variants later is one PR away.

---

## Contributing

Bug reports and PRs welcome. The repository is small enough that you should
be able to read it end-to-end in an afternoon. Please:

* Keep zero runtime dependencies.
* Add a unit test for any new code path.
* Don't add features that require network access.

---

## License

MIT — see [LICENSE](LICENSE).

The English word list (`english.txt`) is reproduced from the official BIP-39
spec and is also MIT-licensed.