# How to Roll a 256-bit BIP-39 Mnemonic by Hand
# 如何用掷骰子生成 256 位 BIP-39 助记词
# サイコロを振って 256ビット BIP-39 mnemonic を生成する方法
# 주사위를 굴려 256비트 BIP-39 니모닉 만들기

> Reading guide: each section is written in English first, then 中文, then 日本語,
> then 한국어.  The numbers and commands are identical in all four.

---

## 0. **Why dice?**  /  为什么要用骰子？  /  なぜサイコロ？  /  왜 주사위인가?

### The reason this guide exists

In **July 2026**, the
[**Coldcard random-number-generator (RNG) vulnerability**](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/)
was disclosed. A single conditional branch in firmware v4.0.1 (released
March 2021) caused the wallet to fall back to a **software pseudo-random
number generator** (`pyb_rng_yasmarang`) instead of the hardware TRNG.
Effectively only **~40 bits** of entropy on the Mk3 (vs. the targeted 128),
and ~72 bits on the Mk4/Mk5/Q. At least **15 attackers** drained
**~1,367 BTC (~$88–111 M)** from ~7,300 addresses in four coordinated
waves.

Among the official remediation steps, **Coinkite itself recommends**
that affected users supplement their seed with **at least 50 manually
rolled dice** to restore genuine randomness. This guide is the
implementation of that recommendation — a complete, reproducible
procedure for going from physical dice rolls to a 256-bit
BIP-39 mnemonic, with full audit trail.

### Why physical randomness at all?

Your computer's CSPRNG is **good**, but you cannot prove to yourself that
it has not been tampered with. A pair of fair dice rolled by your hand
cannot be remotely backdoored — you can see them with your own eyes,
and the entire pipeline is reproducible on paper.

**The math:**

* A fair 6-sided die has `log₂(6) ≈ 2.585` bits of entropy per roll.
* For 256 bits of entropy you therefore need at least
  `⌈256 / log₂(6)⌉ = 99` rolls.
* This guide rolls **100** to leave a small safety margin.
* Coinkite's recommendation of 50 rolls gives ~129 bits, also ample.

If you only have coins, see [Appendix A](#appendix-a--coins--硬币--コイン--동전) below.

---

## 1. English

### What you need

| Item | Why |
|---|---|
| 2 fair dice (d6) | more rolls = less bias |
| Pen + paper | **never** type the rolls into a phone |
| A printed copy of `templates/blank_template.csv` | record each roll as a 0/1 |
| An OFFLINE computer with `bip39_offline_v5.py` | generates the mnemonic at the end |
| A printer or a hand-copy step | the final mnemonic must leave the computer |

### Procedure

1. **Air-gap the computer.** Disconnect Wi-Fi, unplug Ethernet, ideally boot
   a Tails USB stick on a machine that has never touched the internet.
2. Roll **one die** 100 times (or two dice together 50 times).  For each
   roll, write down the outcome (`1`–`6`).
3. Convert each roll to one bit:
   * `1, 2, 3 → 0`
   * `4, 5, 6 → 1`

   This partition is balanced: half the dice faces give 0, half give 1.
   *If you don't trust yourself to be unbiased, do all 100 rolls first and
   then convert later in a separate pass.*
4. You now have 100 bits, which is **not yet 256**.  Repeat steps 2–3
   another 156 times (256 total).  Easier: roll **three times through**
   to get 300 bits, then discard the last 44.
5. Open `templates/blank_template.csv` and fill in the 256 cells row by
   row, group 1 left-to-right, then group 2, … until you reach the end
   of group 23.  Group 24 has only 3 cells.
6. Save the CSV to a USB stick and move it to the offline computer.
7. On the offline computer run:

   ```bash
   python3 bip39_offline_v5.py generate /media/usb/my_entropy.csv
   ```

   The script prints every intermediate step (binary → entropy → SHA-256
   → checksum → 11-bit indices → 24 words).
8. **Verify the checksum** by hand or with a second independent tool
   (e.g. [`iancoleman/bip39`](https://github.com/iancoleman/bip39) running
   on the same offline computer).
9. **Print** the 24-word mnemonic on paper, OR copy it by hand onto a
   metal / paper backup (e.g. *Cryptosteel*).  Then:
   * delete the CSV from the USB,
   * securely wipe the USB (e.g. `shred -n 3 /dev/sdX` on Linux),
   * shut down the offline computer.

### Common pitfalls

* **Don't roll on a soft surface** that can absorb energy and bias the
  outcome.  Use a hard table.
* **Don't reuse dice rolls**.  Every roll must be fresh.
* **Don't read the result aloud**.  Cover your mouth if you speak.
* **Don't photograph the paper** with a phone.

---

## 2. 中文

### 准备工作

| 物品 | 用途 |
|---|---|
| 2 颗公平 6 面骰子 | 越多越能抵消单颗偏差 |
| 笔 + 纸 | **永远不要**用手机记录 |
| 打印好的 `templates/blank_template.csv` | 把每次结果转成 0/1 填入 |
| 一台 **离线电脑** 装好 `bip39_offline_v5.py` | 最后生成助记词 |
| 打印机或手抄步骤 | 24 词必须离开电脑 |

### 操作流程

1. **电脑断网**。拔网线、关 Wi-Fi，最理想是用 Tails 启动盘 + 一台从没上过网的机器。
2. **掷 100 次** 单颗骰子（或者两颗同时掷 50 次），把每次结果（1~6）写在纸上。
3. 把每次结果转成 1 个比特：
   * `1, 2, 3 → 0`
   * `4, 5, 6 → 1`

   这种分法天然平衡——一半的点数对应 0，一半对应 1。*如果你担心自己下意识偏向某种读法，可以先把 100 次结果全记下来，过一会儿再统一转换。*
4. 100 次只有 100 比特，**还不够 256**。再掷 156 次（总共 256 次）；更简单：掷 3 轮共 300 次，最后扔掉 44 比特。
5. 打开 `templates/blank_template.csv`，逐格填入 256 个比特：从 group1 的 c1 → c11，到 group23 结束。group24 只填 3 列。
6. 把 CSV 存到 U 盘，插到离线电脑。
7. 在离线电脑上执行：
   ```bash
   python3 bip39_offline_v5.py generate /media/usb/my_entropy.csv
   ```
   脚本会一步步打印：二进制 → 熵 → SHA-256 → 校验和 → 11 位索引 → 24 词。
8. **手算或用第二个独立工具核对校验和**（比如同一台离线电脑上的 [`iancoleman/bip39`](https://github.com/iancoleman/bip39)）。
9. **打印**24 词到纸上，**或手抄**到金属助记词板（Cryptosteel 等）。然后：
   * 删除 U 盘上的 CSV；
   * 安全擦除 U 盘（Linux 上：`shred -n 3 /dev/sdX`）；
   * 关机。

### 常见错误

* **不要在软垫上掷**，会被吸收能量。硬的桌子最好。
* **不要复用任何一次结果**，每次都必须是新掷的。
* **不要朗读出来**。如果要说话请捂嘴。
* **不要用手机拍那张纸**。

---

## 3. 日本語

### 必要なもの

| アイテム | 用途 |
|---|---|
| 公正な 6 面サイコロ 2 個 | 多いほど偏りを相殺 |
| ペンと紙 | **絶対に** スマホに入力しない |
| 印刷済みの `templates/blank_template.csv` | 各試行を 0/1 として記録 |
| **オフライン PC** に `bip39_offline_v5.py` 導入済み | 最後に mnemonic を生成 |
| プリンタまたは手書きコピー手順 | 24 語は PC から外に出す |

### 手順

1. **PC をエアギャップ化**。LAN ケーブルを抜き、Wi-Fi をオフ。可能なら Tails USB で、まだ一度もネットにつないだことのないマシンから起動。
2. サイコロ 1 個を **100 回** 振る（または 2 個同時に 50 回）。各回の出目（1〜6）を紙に書く。
3. 各出目を 1 ビットに変換:
   * `1, 2, 3 → 0`
   * `4, 5, 6 → 1`

   この分割は均衡している — 出目の半分が 0、残りが 1。*自分の判断が偏っている気がするなら、まず 100 回全部記録し、後で一気に変換する。*
4. 100 回では 100 ビット、**まだ 256 に足りない**。さらに 156 回振る（合計 256 回）。より簡単: 3 周して合計 300 ビット、最後の 44 ビットを捨てる。
5. `templates/blank_template.csv` を開き、256 マスに書き込む: group1 の c1 → c11、group2 … group23 まで。group24 は 3 マスだけ。
6. CSV を USB に保存し、オフライン PC に挿す。
7. オフライン PC で実行:
   ```bash
   python3 bip39_offline_v5.py from-dice /media/usb/my_entropy.csv
   ```
   スクリプトは各段階をすべて表示（バイナリ → エントロピー → SHA-256 → チェックサム → 11 ビットインデックス → 24 単語）。
8. **チェックサムを別の実装で検証**（同じオフライン PC 上の [`iancoleman/bip39`](https://github.com/iancoleman/bip39) など）。
9. 24 語の mnemonic を **印刷** するか、金属バックアップ（*Cryptosteel* 等）に **手書き**。その後:
   * USB の CSV を削除；
   * USB を完全消去（Linux: `shred -n 3 /dev/sdX`）；
   * シャットダウン。

### よくあるミス

* **柔らかい面** で振らない。机のような硬い面で。
* **同じ出目を再利用しない**。毎回新鮮に振る。
* **読み上げない**。話すなら口を覆う。
* **スマホで紙を撮らない**。

---

## 4. 한국어

### 필요한 것

| 항목 | 용도 |
|---|---|
| 공정한 6면 주사위 2개 | 많을수록 편향 상쇄 |
| 펜 + 종이 | **절대** 휴대전화에 입력하지 않음 |
| 출력된 `templates/blank_template.csv` | 각 결과를 0/1로 기록 |
| **오프라인 PC** 에 `bip39_offline_v5.py` 설치 | 마지막에 니모닉 생성 |
| 프린터 또는 손글씨 복사 절차 | 24단어는 PC 밖으로 나가야 함 |

### 절차

1. **PC를 에어갭**합니다. LAN 케이블을 뽑고 Wi-Fi를 끄세요. 가능하면 Tails USB로, 한 번도 인터넷에 연결된 적 없는 기기에서 부팅.
2. 주사위 1개를 **100번** 굴립니다 (또는 2개를 동시에 50번). 매번 결과 (1~6)를 종이에 적습니다.
3. 각 결과를 1비트로 변환:
   * `1, 2, 3 → 0`
   * `4, 5, 6 → 1`

   이 분할은 균형 잡혀 있습니다 — 면의 절반이 0, 나머지가 1. *본인의 판단이 편향될까 걱정된다면, 먼저 100번을 모두 기록한 후 나중에 한꺼번에 변환하세요.*
4. 100번은 100비트, **256에 부족**. 156번을 더 굴립니다 (총 256번). 더 간단한 방법: 3바퀴 굴려 300비트, 마지막 44비트를 버립니다.
5. `templates/blank_template.csv` 를 열고 256칸을 채웁니다: group1의 c1 → c11, group2 … group23까지. group24는 3칸만.
6. CSV를 USB에 저장하고 오프라인 PC에 삽입.
7. 오프라인 PC에서 실행:
   ```bash
   python3 bip39_offline_v5.py from-dice /media/usb/my_entropy.csv
   ```
   스크립트가 각 단계를 모두 표시 (바이너리 → 엔트로피 → SHA-256 → 체크섬 → 11비트 인덱스 → 24단어).
8. **체크섬을 다른 구현으로 검증** (같은 오프라인 PC의 [`iancoleman/bip39`](https://github.com/iancoleman/bip39) 등).
9. 24단어 니모닉을 **인쇄** 하거나 금속 백업 (*Cryptosteel* 등)에 **손글씨** 로 기록. 이후:
   * USB의 CSV 삭제;
   * USB 완전 삭제 (Linux: `shred -n 3 /dev/sdX`);
   * 종료.

### 흔한 실수

* **부드러운 면** 에서 굴리지 마세요. 단단한 책상이 좋습니다.
* **같은 결과를 재사용하지 마세요**. 매번 새로 굴립니다.
* **소리 내어 읽지 마세요**. 말하려면 입을 가리세요.
* **휴대전화로 종이를 찍지 마세요**.

---

## Appendix A — coins  /  硬币  /  コイン  /  동전

A fair coin has 1 bit per flip.  You need **at least 256 flips**.

```bash
# Write H or T, one per line, into flips.txt:
#   H
#   T
#   H
#   ...

python3 bip39_offline_v5.py from-dice   # NOT YET SUPPORTED FOR COINS
```

Workaround until the coin CLI is wired up:

```python
import bip39_offline_v5 as bip39
with open("flips.txt") as f:
    flips = [line.strip() for line in f if line.strip()]
entropy = bip39.coin_flips_to_entropy(flips)
mnemonic = bip39.entropy_to_mnemonic(entropy)
print(" ".join(mnemonic))
```

(You can paste this into a `coin.py` file on the offline machine and run
`python3 coin.py`.)

---

## Appendix B — cards  /  扑克牌  /  トランプ  /  카드

A single shuffled 52-card deck encodes only `log₂(52!) ≈ 225.6` bits — **not
enough**.  Use **two** decks (104 cards, ~451 bits).  Pass the cards in
bridge order notation: `A♣ 2♣ … K♣ A♦ 2♦ … K♦ A♥ … K♥ A♠ … K♠`, e.g.
`Ac 2c 3c ... Ks`.

```python
import bip39_offline_v5 as bip39

# First deck, top-to-bottom as you turned them face-up
deck1 = ["Ac", "5d", "Ts", ...]   # 52 cards
# Second deck (must be independent)
deck2 = ["Kc", "9d", "2h", ...]   # 52 cards

entropy = bip39.cards_to_entropy(deck1 + deck2)
mnemonic = bip39.entropy_to_mnemonic(entropy)
```

Cards are convenient because you can shuffle them anywhere with your hands,
but the entropy density per object is lower than dice.

---

*Last updated: alongside the 1.0.0 release.*