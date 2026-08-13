# BIP-39 256ビット・エントロピー mnemonic 生成ツール（24語 / Bitcoin 標準）

> **依存関係ゼロ・監査可能・初心者にも扱いやすい BIP-39 完全実装（256ビット / 24語）。**
>
> オフライン優先 · 1行ずつ読める · 知識ゼロでもOK

**Languages:** [English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

**ランタイム国際化：** CLI / インタラクティブ モードは `LANG` / `LC_ALL` /
`BIP39_LANG` 環境変数から自動的に言語を検出し、英語 / 简体中文 / 日本語
でプロンプトを出力します。他の locale はすべて英語にフォールバックします。
`BIP39_LANG=ja python3 bip39_offline_v5.py ...` で強制指定も可能です。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-BIP--39%20vectors%20passing-brightgreen.svg)](docs/BIP39-math.md)

---

## なぜこのプロジェクト？

**2026 年 7 月**、Bitcoin コミュニティはハードウェアウォレット史上最も
**恥ずべき公開失敗**に直面しました —— [Coldcard の乱数生成器（RNG）脆弱性](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/)。

2021 年 3 月 17 日にリリースされたファームウェア v4.0.1 において、
`MICROPY_HW_ENABLE_RNG = 0` という 1 行の設定と、マクロの**値**ではなく
**存在**のみをチェックする条件分岐により、ウォレットのシード生成器が
ハードウェア TRNG ではなく MicroPython の `pyb_rng_yasmarang`
（**ソフトウェア疑似乱数生成器**) を呼び出すようになっていました。
このバグは GitHub 上で**5 年間**も潜伏していました。

被害の実態：

- **Mk3** の有効エントロピーが 128 bit から **~40 bit** に低下（約 1 兆通り、
  現代の GPU クラスターなら**数時間**で全探索可能）
- **Mk4 / Mk5 / Q** は **~72 bit**
- **2026 年 7 月 30–31 日**、少なくとも **15 名の独立攻撃者**が連携して
  **4 波**の攻撃を仕掛け、約 **7,300 アドレス**から合計 約 **1,367 BTC**
  （当時のレートで**約 1.1 億ドル**）を流出
- **第 1 波**は Coinkite 公式警告の**30 時間前**に始まり、30 分で ~500 ウォレット
  を空にした
- Reddit の開発者が Claude Code でスキャンしたところ、**わずか 8 分**で
  5 年間潜伏していたこのバグを再現

Coldcard 事件は 3 つの安心神話を同時に破壊しました：

1. **「ハードウェアウォレットは構造的に安全」** —— 違います。シードは
   ソフトウェアであり、ソフトウェアにはバグがあります。
2. **「オープンソースだから安全」** —— 原則的にはそうですが、実際には 5 年間
   GitHub にあったのに誰も気づきませんでした。
3. **「ファームウェアを更新すれば良い」** —— できません。パッチは**今後**の
   生成を修正するだけで、既に作られてしまった壊れたシードは**永久に**壊れた
   ままです。

より深い教訓は、**いかなるベンダー——どれだけ有名でも——あなたの財産を守る
エントロピーの責任を負えない**ということです。**完全に自分で検証できる
信頼仮定は、乱数源そのもの**だけです。

このリポジトリは、まさにこの教訓への回答です。**ネットから切断したパソコンで、
1 行ずつコードを確認しながら mnemonic を生成する**ことができます。

- ✅ Trezor / Ledger / MetaMask / Electrum / Sparrow / BlueWallet と完全互換
- ✅ 256 ビット（24 語）= 主要ハードウェアウォレットのデフォルト強度
- ✅ ランタイム依存ゼロ（Python 標準ライブラリのみ）
- ✅ オフライン モードは**ディスクを読まず、書きません** — エントロピーは
  プロセスメモリにのみ存在
- ✅ 8 件の NIST SP 800-22 統計テスト（コア 5 + 補助 3）で収集したエントロピーを
  検証
- ✅ サイコロ・コイン・トランプ・CSV など多様なエントロピー源に対応
- ✅ ネットワーク通信は一切なし
- ✅ ランタイム自動言語検出（English / 简体中文 / 日本語）

---

## リポジトリ構成

```
bip39-256bit-entropy-mnemonic/
├── README.md                  ← 英語版
├── README.zh-CN.md            ← 简体中文
├── README.ja.md               ← このファイル（日本語）
├── HOWTO-dice.md              ← サイコロ生成の完全ガイド
├── BACKGROUND.md              ← プロジェクト背景：Coldcard 2026 事件
├── SECURITY.md                ← 脅威モデル & ベストプラクティス
├── LICENSE                    ← MIT
├── english.txt                ← BIP-39 公式 2048 単語リスト
├── bip39_offline_v5.py        ← 機能全部入り単一ファイル（1470 行）
├── examples/
│   ├── demo_zero_entropy.csv  ← "abandon…art" を生成
│   └── example_full.csv       ← 非ゼロのサンプル
├── templates/
│   └── blank_template.csv     ← 空欄テンプレート
└── docs/
    └── BIP39-math.md          ← アルゴリズム可視化解説
```

---

## 30秒で始める

```bash
# 1. 一度もネットにつないだことのない PC で clone（または zip ダウンロード）
# 2. デモ CSV を実行（エントロピー全ゼロ → "abandon × 23, art"）
python3 bip39_offline_v5.py generate examples/demo_zero_entropy.csv

# 3. BIP-39 公式テストベクトルで挙動確認（generate は examples/demo_zero_entropy.csv を使った）
```

デモが動作することを確認したら：

1. `templates/blank_template.csv` を USB でオフライン PC へコピー；
2. オフライン PC で表計算ソフトに開き、エントロピーを手作業で記入；
3. `python3 bip39_offline_v5.py generate my_entropy.csv` を実行；
4. **結果を印刷** → **紙に手書き** → **PC 上のファイルを完全消去**。

---

## インストール

何もインストール不要。Python ≥ 3.7 だけ必要です。

```bash
git clone https://github.com/qianmyth/bip39-256bit-entropy-mnemonic.git
cd bip39-256bit-entropy-mnemonic
python3 -m unittest discover -s tests    # 任意：動作確認
```

macOS Numbers ファイルを直接読みたい場合のみ：

```bash
pip install numbers-parser    # ネット接続可能な PC で一度だけ、その後オフライン PC へ
```

---

## 使い方

### A. サイコロ（最も安全 / 完全人力）

詳細は [`HOWTO-dice.md`](HOWTO-dice.md)。簡易版：

```bash
# rolls.txt にサイコロの結果を 1 行ずつ記入：
#   4
#   6
#   1
#   3
#   ...

python3 bip39_offline_v5.py from-dice rolls.txt
```

スクリプトが 32 バイトのエントロピーと 24 語の mnemonic を表示します。**100 回投げた公正な 6 面サイコロ ≈ 258.5 ビット** で十分です。

### B. 手書き CSV

`templates/blank_template.csv` を開く：

|          | c1 | c2 | c3 | … | c11 |
|----------|----|----|----|---|-----|
| group1   | 0  | 0  | 0  | … | 0   |
| …        | …  | …  | …  | … | …   |
| group24  | 0  | 0  | 0  |   |     |

- 24 行 × 11 列、合計 256 マスを 0 / 1 で手書き。
- 0 = 空欄 / 0、1 = マーク / 1。
- 24 行目は 3 列だけ記入。

```bash
python3 bip39_offline_v5.py generate my_entropy.csv
```

出力には各ステップが表示されます：
```
24 組バイナリ  →  256 ビット  →  SHA-256  →  8 ビットチェックサム  →  264 ビット
              →  24 × 11 ビット  →  10進インデックス  →  24 単語
```

### C. 既存 mnemonic の検証

```bash
# 検証
python3 bip39_offline_v5.py validate "abandon abandon ... art"
# → checksum: VALID ✓

# 512 ビット seed も表示（TREZOR passphrase）
python3 bip39_offline_v5.py validate --show-seed --passphrase TREZOR \
    "abandon abandon ... art"
# → seed (BIP-39, passphrase='TREZOR'): bda8…cc8
```

### D. Python ライブラリとして使用

```python
import bip39_offline_v5 as bip39

entropy = bip39.dice_rolls_to_entropy([3, 5, 6, 1, 2, 4, ...])
mnemonic = bip39.entropy_to_mnemonic(entropy)
assert bip39.validate_mnemonic(mnemonic)
seed = bip39.mnemonic_to_seed(mnemonic, passphrase="optional-passphrase")
```

---

## アルゴリズム概要

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │  256 ビット  ─→  SHA-256  ─→  先頭 8 ビット  =  8 ビットチェックサム │
 │                                                                      │
 │  (256) ++ (8)  =  264 ビット                                         │
 │                                                                      │
 │  24 × 11 ビットに分割  ─→  24 個のインデックス (0~2047)              │
 │                                                                      │
 │  インデックス → english.txt[index]  =  24 単語                       │
 └──────────────────────────────────────────────────────────────────────┘
```

可視化版は `docs/BIP39-math.md`。

---

## テスト

```bash
python3 -m unittest discover -s tests -v
```

**12/12 OK** が出るはず。4 件のベクトルは
[`trezor/python-mnemonic/vectors.json`](https://github.com/trezor/python-mnemonic/blob/master/vectors.json) 直系で、Trezor / Ledger と seed が完全一致します。

---

## セキュリティ（必読）

1. **必ずネット未接続 PC で実行** — キーロガーや画面キャプチャマルウェアに一瞬でも感染する可能性があります。Tails 起動 USB + ネット未経験マシンが理想。
2. **チェックサムを目視確認** — 別実装（[`iancoleman/bip39`](https://github.com/iancoleman/bip39) オフライン版）と比較。
3. **BIP-39 passphrase（25 番目の単語）を必ず設定** — 設定しないと 24 語を拾った人 = あなたのコイン。設定すると忘れても復元不可。**別保管が鉄則**。
4. **大金はエントロピー源を二重化**（サイコロ＋コインなど、相互検証）。
5. **ネット接続 PC で本物の mnemonic を絶対入力しない**。`--show-seed` はデバッグ専用。

詳細は [`SECURITY.md`](SECURITY.md)。

---

## ライセンス

MIT — [LICENSE](LICENSE) を参照。

`english.txt` は BIP-39 公式仕様から取得しており、同じく MIT ライセンスです。