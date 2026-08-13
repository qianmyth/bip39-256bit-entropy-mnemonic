# BIP-39 algorithm walk-through

This document explains, step by step, how 256 bits of entropy become a
24-word mnemonic and back.  We use the all-zeros entropy as our worked
example, because its output is the famous canonical sentence:

> abandon abandon abandon abandon abandon abandon abandon abandon abandon
> abandon abandon abandon abandon abandon abandon abandon abandon abandon
> abandon abandon abandon abandon abandon **art**

---

## 1. Inputs / outputs

| Input | Output |
|-------|--------|
| 32 bytes (256 bits) of entropy | 24 English words from the BIP-39 wordlist |
| 24 English words + optional passphrase | 64 bytes (512 bits) of seed |
| 24 English words (without seed) | 32 bytes of entropy + checksum validation |

The 24-word sentence is **the wallet's "master key"**. Lose it, lose your
coins.  Anyone who reads it, owns your coins.

---

## 2. Step 1: 256 bits of entropy

We start with a uniformly-random byte string of length 32.

```
ENT  = 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000
       └───────────────────────────────────────────────────────────────────┘
                                       32 bytes  =  256 bits
```

---

## 3. Step 2: SHA-256 checksum

BIP-39 uses the first `ENT / 32 = 8` bits of `SHA-256(ENT)` as a checksum.
This is a tiny error-detection code: any random typo has only a 1-in-256
chance of producing a sentence that *looks* valid.

```
SHA-256(00000000…00) = 5df6e0e2761359d30a8275058e299fcc0381534545f55cf43e41983f5d4c9457

Take the first byte: 0x5d = 01011101

So the 8-bit checksum is:

       CS  = 01011101
```

---

## 4. Step 3: 264 bits → 24 × 11-bit indices

Concatenate entropy and checksum, then split into 24 groups of 11 bits:

```
ENT || CS  =  00000000000000000000000000000000000000000000000000000000000000000 01011101
              └──────────────── 256 bits ────────────────┘ └─ 8 bits ─┘

Split into 24 × 11 bits:

   segment  1 : 00000000000  = 0    → "abandon"
   segment  2 : 00000000000  = 0    → "abandon"
   segment  3 : 00000000000  = 0    → "abandon"
   …
   segment 23 : 00000000000  = 0    → "abandon"
   segment 24 : 00001011101  = 189  → "art"
```

(Each segment is the integer value of 11 binary digits, between 0 and 2047,
used as an index into the 2048-word English list.)

---

## 5. Step 4: index → word

`english.txt` is sorted alphabetically.  The first 11 indices in the
zero-entropy example are all `0`, mapping to `"abandon"`.  The last segment
is binary `00001011101` = 189 (decimal), which is the 190th line of
`english.txt` (1-indexed), the word `"art"`.

```
abandon abandon abandon abandon abandon abandon abandon abandon abandon
abandon abandon abandon abandon abandon abandon abandon abandon abandon
abandon abandon abandon abandon abandon art
```

That's the BIP-39 mnemonic.

---

## 6. Step 5: mnemonic → seed (BIP-39 §"From mnemonic to seed")

The seed is **not** just the entropy — it is a 512-bit value derived from
the mnemonic and an *optional* passphrase, using PBKDF2-HMAC-SHA512 with
2048 iterations.

```
seed = PBKDF2(
    password = NFKD(" ".join(mnemonic)),
    salt     = "mnemonic" + NFKD(passphrase),
    iter     = 2048,
    prf      = HMAC-SHA512,
    dklen    = 64,
)
```

For the all-zero entropy with passphrase `"TREZOR"`, the seed (in hex) is:

```
bda85446c68413707090a52022edd26a1c9462295029f2e60cd7c4f2bbd3097
170af7a4d73245cafa9c3cca8d561a7c3de6f5d4a10be8ed2a5e608d68f92fcc8
```

This is the seed that any BIP-32 HD wallet (Trezor, Ledger, MetaMask,
Electrum, Sparrow, …) would use to derive the first address.  Cross-check
with `trezor/python-mnemonic/vectors.json` if you want extra confidence.

---

## 7. Reversing the algorithm

To go back from a 24-word mnemonic to 32 bytes of entropy:

1. Look up each word's index in `english.txt`.
2. Concatenate the 24 × 11-bit indices into a 264-bit integer.
3. The lowest 8 bits are the checksum; the top 256 bits are the entropy.
4. Recompute `SHA-256(entropy)`, take its top 8 bits, and compare to the
   stored checksum.  If they differ, the sentence is corrupt.

The single-file implementation does this in `bip39_offline_v5.py`.
(The reference is the historical `mnemonic_to_entropy()` function.)

---

## 8. Why 256 bits?

The BIP-39 spec also allows 128, 160, 192 and 224-bit entropy, producing
12 / 15 / 18 / 21-word sentences respectively. 256 bits (24 words) is the
**maximum** and the default on every modern hardware wallet, because:

* It is exactly the security level of an uncompressed Bitcoin private key
  (~2²⁵⁶ ≈ 10⁷⁷ attempts to brute-force).
* 24 words on paper or metal are still practical to write down by hand.
* The checksum is 8 bits, giving `1 / 256` random-error tolerance.

BIP-39 official test vectors (the same ones used by `trezor/python-mnemonic`)
are embedded in `bip39_offline_v5.py` and verified at run time via
`python3 bip39_offline_v5.py validate "abandon × 23, art"`. The code
supports the 256-bit path only; shorter variants would require only
a few lines of additional logic.

---

## 9. References

* BIP-39: <https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki>
* Reference implementation (Trezor): <https://github.com/trezor/python-mnemonic>
* Test vectors: <https://github.com/trezor/python-mnemonic/blob/master/vectors.json>