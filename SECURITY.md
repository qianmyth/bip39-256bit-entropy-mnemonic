# Security & Threat Model

## Why this document exists

In **July 2026** the
[**Coldcard random-number-generator (RNG) vulnerability**](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/)
taught the entire industry a hard lesson: **even on a hardware wallet
with a real TRNG, the seed is still produced by software**, and that
software can have a five-year-old bug that turns "256 bits of entropy"
into "40 bits of entropy". At least **15 attackers** drained
**~1,367 BTC (~$88–111 M)** from ~7,300 addresses in four coordinated
waves before the public warning was issued.

The threat model below is what **this project** protects against, and
what it does **not**.

## Threat model

You are about to generate the master key to a cryptocurrency wallet.  An
attacker who learns the 24-word mnemonic owns every coin you will ever
deposit at that address.  This document lists the realistic threats and the
mitigations baked into this project.

| # | Threat | Mitigation |
|---|--------|-----------|
| 1 | Malware on your everyday OS reads the mnemonic as you type / generate it | Run the tool on an **air-gapped** computer; see §1. |
| 2 | The tool itself is malicious (backdoor, hidden seed pattern) | The whole source fits on one screen — read it.  Run an independent BIP-39 tool (e.g. `iancoleman/bip39` offline) and compare. |
| 3 | **Hardware RNG or CSPRNG is compromised or bypassed by a software bug** (Intel ME, AMD PSP, supply chain, **or a firmware conditional-branch defect like Coldcard 2026**) | Use **dice / coins / cards** as the entropy source. Never trust a single vendor's RNG without an independent physical sanity check. |
| 4 | Cosmic-ray / power glitches produce a biased `os.urandom` output | The CSV / dice workflow is auditable: you can re-roll if a value looks wrong. |
| 5 | Loss of the mnemonic | **Add a BIP-39 passphrase (the 25th word) and store it separately.**  Make at least two paper / metal backups in different physical locations. |
| 6 | Theft of the mnemonic | Same as #5, plus keep the backups **invisible** (no marking on the envelope). |
| 7 | Coercion / "wrench attack" | Use a passphrase that you can plausibly deny; store decoy wallets with smaller balances. |
| 8 | Shoulder surfing during backup | Cover the paper; never read it aloud; never photograph with a phone. |
| 9 | Memory / swap / hibernate leaks on the offline PC | Boot a live USB (Tails), generate, shut down.  Never hibernate.  Wipe the USB stick before reconnecting to the internet. |
| 10 | Supply-chain attack on this repository itself | Pin to a commit hash; verify the SHA-256 of `english.txt` against [the BIP-39 spec](https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt). |
| 11 | A wallet vendor's RNG fallback returns low-entropy seeds (the Coldcard scenario) | Always cross-check by also generating a fresh seed with this tool using **physical dice**, then compare the addresses you derive. Both should match; if they don't, the wallet's RNG is suspect. |

## §1  Recommended hardware setup

* A laptop that has **never** been online (Lenovo ThinkPad X230, removed
  Wi-Fi card, running Tails from USB).
* OR a Raspberry Pi with no network, running Raspberry Pi OS Lite.
* OR a cheap, freshly wiped Windows machine booted from a Tails USB stick.
* Whatever you choose, run with the Wi-Fi and Bluetooth hardware kills
  switch engaged.  If unsure, put the machine inside a Faraday bag.

## §2  Workflow checklist

```
[ ] 1. Boot a live USB OS (e.g. Tails) on a clean machine.
[ ] 2. Disable Wi-Fi and Bluetooth in firmware.
[ ] 3. Verify the SHA-256 of this repository matches what you downloaded.
[ ] 4. Run: python3 bip39_offline_v5.py generate examples/demo_zero_entropy.csv
[ ]      → output is exactly "abandon × 23, art".
[ ] 5. Roll 100 dice / flip 256 coins by hand.  Write each on paper.
[ ] 6. Convert to bits and fill templates/blank_template.csv (offline).
[ ] 7. python3 bip39_offline_v5.py generate my_entropy.csv
[ ] 8. Independently verify the 24-word mnemonic with `bip39_offline_v5.py validate`
[ ]      (or iancoleman/bip39 offline).
[ ] 9. Also audit the entropy: `bip39_offline_v5.py check-entropy my_entropy.csv`
[ ]      → all 5 core tests should pass.
[ ] 10. Print the 24-word mnemonic. (Or handwrite on metal.)
[ ] 11. Add a BIP-39 passphrase (the 25th word).  Write it on a SEPARATE paper.
[ ] 12. Shut down.  Wipe the USB.  Store the two papers in different places.
```

## §3  What this code does *not* do

* It does **not** contact the network.
* It does **not** read or write anything outside the file paths you give it.
* It does **not** invoke `subprocess`, `ctypes`, or any third-party library.
* It does **not** log anything to disk.
* It does **not** keep entropy / mnemonic in any global state.

You can confirm this with:

```bash
$ grep -E "import (urllib|requests|http|socket|subprocess|ctypes)" bip39_offline_v5.py
# (empty)
```

## §4  Disclosure

If you find a real vulnerability in this code, please open a private issue
or contact the maintainer.  Do **not** post it publicly before a fix is
available.

## §5  Disclaimer

This software is provided "as is", without warranty of any kind.  You are
solely responsible for the security of your own funds.  Always cross-check
with multiple independent tools and never entrust life-changing amounts to
a single workflow.