# Background — Why we built this  /  项目背景

## 1. English

### Why this project exists

In **July 2026** the Bitcoin community was hit by one of the most
embarrassing hardware-wallet failures ever made public: the
[**Coldcard random-number-generator (RNG) vulnerability**](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/).

* **What happened.** In firmware **v4.0.1**, released on **March 17, 2021**,
  a one-line configuration change — `MICROPY_HW_ENABLE_RNG = 0` combined
  with a conditional branch that only checked the macro's *existence*
  rather than its *value* — caused the wallet-seed generator to call
  `pyb_rng_yasmarang`, a **software pseudo-random number generator**,
  instead of the device's hardware true-random number generator (TRNG).
* **How long it lasted.** The bug shipped in March 2021 and was not
  publicly disclosed until **July 30, 2026** — over **five years**.
* **Affected devices.** Coldcard **Mk2 / Mk3 / Mk4 / Mk5 / Q** running
  firmware from 4.0.1 onward. (TAPSIGNER, OPENDIME, SATSCARD were not
  affected.) All affected units were **still** producing low-entropy
  seeds up to the patch day.
* **Effective entropy dropped**.
  * Mk3: about **40 bits** of effective entropy (target: 128 bits).
  * Mk4 / Mk5 / Q: about **72 bits**.
  * 40 bits ≈ 1 trillion possibilities. A modern GPU farm burns through
    that in **hours, not centuries**.
* **Damage.** On **July 30–31, 2026**, at least **15 distinct attackers**
  swept roughly **1,367 BTC** (~**$88–111 million USD** at the time)
  out of **~7,300 vulnerable addresses** in four coordinated waves.
  The first wave drained ~500 wallets (~594 BTC) in under 30 minutes
  *before* Coinkite's public warning was issued.
* **AI-assisted discovery.** A Reddit developer used Claude Code to
  audit the open-source firmware after the disclosure and reproduced
  the flaw in **8 minutes** — proving that the bug had been hiding in
  plain sight on GitHub for years.
* **Coldcard's own post-mortem recommendation** is to **manually roll
  at least 50 physical dice** to add genuine randomness, and migrate
  to a freshly generated seed on a patched device.

Sources: [Coinkite advisory](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/),
[Block engineering writeup](https://engineering.block.xyz/blog/predictable-rng-fallback-and-32-bit-reseed-in-coldcard-firmware),
[Galaxy Digital on-chain analysis](https://www.galaxy.com/),
[BleepingComputer](https://www.bleepingcomputer.com/news/security/coldcard-wallet-rng-flaw-likely-linked-to-88-million-bitcoin-theft/).

### The lesson: "offline" ≠ "secure"

The Coldcard incident refuted three comforting myths simultaneously:

1. **"Hardware wallets are secure by construction."** They are not.
   The seed is software, and software has bugs.
2. **"Open-source firmware is safer."** In principle, yes. In practice,
   Coldcard's firmware was on GitHub the entire time and the bug
   survived five years of community review.
3. **"Just upgrade the firmware."** It does not work. The patch fixes
   *future* generation, but every seed already produced by the broken
   RNG is still broken. The only cure is to **generate a new seed on
   a patched device** and **migrate the funds**.

The deeper lesson is that **no vendor — no matter how reputable —
can take responsibility for the entropy that protects your money**.
The only trust assumption you can fully verify yourself is the
randomness source itself.

### What this project is, in light of Coldcard

Given that lesson, the goal of this repository is to give you a tool
that satisfies exactly the properties a Coldcard user could not get
from their device:

* **Zero dependencies.** Only the Python standard library, which means
  you can read every line before running it.
* **Offline by construction.** The "interactive" subcommand writes
  nothing to disk and accepts nothing from disk — the entropy you
  collect lives in process memory and is wiped when you close the
  terminal.
* **Human-verifiable entropy.** Coin flips, dice rolls, or a shuffled
  card deck are physical processes. You can audit the experiment
  yourself and convince yourself the source is fair.
* **NIST SP 800-22 quality check.** After you collect 256 bits, the
  tool runs 8 statistical tests (frequency, runs, longest-run,
  autocorrelation, pattern detection, plus 3 auxiliary tests) and
  tells you whether the sample looks healthy. If a core test fails,
  you can choose to discard the entropy and re-run.
* **Mathematically transparent.** The BIP-39 algorithm is implemented
  here in ~100 lines of pure Python, accompanied by `docs/BIP39-math.md`
  that walks you through every step on paper.

### What this project is NOT

* **Not a wallet.** It does not derive keys, manage UTXOs or sign
  transactions. After you have your 24-word mnemonic, **import it**
  into [Sparrow](https://sparrowwallet.com/), [Electrum](https://electrum.org/),
  [Bitcoin Core](https://bitcoincore.org/) or a hardware wallet
  whose firmware you trust.
* **Not a substitute for firmware updates.** If you own a Coldcard,
  update its firmware **first**; the patched firmware is required to
  ensure the device doesn't clobber your good entropy with its broken
  RNG. Generate the mnemonic offline on a clean computer, then
  re-import.
* **Not affiliated with Coinkite, Block, Trezor, Ledger, SatoshiLabs,
  or any other wallet vendor.** All wordlist and algorithm references
  are made under the MIT-licensed BIP-39 specification.
* **Not a guarantee that your seed is safe.** A 24-word mnemonic is
  only as strong as the entropy that produced it. This tool helps
  you verify your entropy, but **you** are the final auditor.

### TL;DR

> Coldcard taught the entire industry that the chain of trust
> collapses at the entropy source. This project hands you a small,
> readable tool so **you** can be the entropy source.

---

## 2. 中文

### 这个项目为什么存在

**2026 年 7 月**，比特币社区经历了硬件钱包史上**最尴尬的一次公开失败**：
[ **Coldcard 随机数生成器（RNG）漏洞**](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/) 。

* **发生了什么。** 2021 年 3 月 17 日发布的固件 **v4.0.1** 中，一行配置
  `MICROPY_HW_ENABLE_RNG = 0` 配合一段只判断"宏**是否存在**"而非"宏**值**是什么**"
  的条件分支，导致钱包种子生成函数调用了 `pyb_rng_yasmarang` —— 一个
  **软件伪随机数生成器（PRNG）**，而非设备内置的硬件真随机数发生器（TRNG）。
* **潜伏了多久。** 漏洞 2021 年 3 月上线，直到 **2026 年 7 月 30 日**才被
  公开披露 —— **五年多**。
* **哪些设备受影响。** Coldcard **Mk2 / Mk3 / Mk4 / Mk5 / Q**，运行自
  v4.0.1 起到补丁日为止的所有固件。（TAPSIGNER / OPENDIME / SATSCARD 不受影响。）
  在补丁发布前，所有受影响的设备**仍然**在生成低熵种子。
* **熵值掉了多少**。
  * Mk3：有效熵约 **40 bit**（目标 128 bit）。
  * Mk4 / Mk5 / Q：约 **72 bit**。
  * 40 bit ≈ 1 万亿种可能。**现代 GPU 集群几小时就能穷举完**，而不是几个世纪。
* **损失。** **2026 年 7 月 30–31 日**，至少 **15 个独立攻击者**协调发起
  **4 波攻击**，从约 **7,300 个**脆弱地址中扫走约 **1,367 BTC**（折合当时
  **8,800 万–1.11 亿美元**）。**第一波** 仅用 30 分钟就清空了 ~500 个钱包
  （约 594 BTC），**早于 Coinkite 官方公告**整整 30 个小时。
* **AI 协助的发现。** 一位 Reddit 开发者用 Claude Code 在公开固件上扫描，
  **仅 8 分钟**就复现了漏洞 —— 证明这个 bug 一直在"公开处"隐藏了五年。
* **Coldcard 官方事后建议**：**手动掷至少 50 次骰子**补充真实随机数，并在
  修复后的设备上**重新生成**种子。

资料来源：[Coinkite 公告](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/)、
[Block 工程分析](https://engineering.block.xyz/blog/predictable-rng-fallback-and-32-bit-reseed-in-coldcard-firmware)、
[Galaxy Digital 链上分析](https://www.galaxy.com/)、
[BleepingComputer 报道](https://www.bleepingcomputer.com/news/security/coldcard-wallet-rng-flaw-likely-linked-to-88-million-bitcoin-theft/)。

### 教训："离线" ≠ "安全"

Coldcard 事件一次性戳穿了三个让人安心的迷信：

1. **"硬件钱包天生安全。"** 错。种子终究是软件生成的，而软件有 bug。
2. **"开源固件更安全。"** 原则上对，但实践中 Coldcard 固件一直挂在 GitHub 上，
   这个 bug 在社区审阅下**活了五年**。
3. **"升级固件就行。"** 不行。补丁只修复**今后**生成的种子；已经用坏 RNG 生成的
   那些种子**永远**是坏的。唯一正确做法是**在已修复设备上重新生成种子**，
   并**迁移资金**。

更深层的教训是：**没有任何厂商——无论多有名——能对保护你财产的熵源负责**。
唯一你能完全验证的信任假设，就是**随机源本身**。

### Coldcard 之后，本项目是什么

基于这个教训，本仓库的目标是给你一个工具，**满足 Coldcard 用户从他们设备上
得不到的那些性质**：

* **零依赖。** 仅 Python 标准库，**运行前你能逐行读完所有代码**。
* **离线天然属性。** `interactive` 子命令**不读盘、不写盘**——你收集的熵
  只存在于进程内存中，关闭终端即清除。
* **人可验证的熵源。** 硬币、骰子、洗牌——都是物理过程。你可以亲自审查
  实验过程，说服自己源头是公平的。
* **NIST SP 800-22 熵质量检查。** 收集完 256 位后，工具自动跑 8 项统计
  测试（频率、游程、最长游程、自相关、模式检测 + 3 项辅助），告诉你
  样本是否健康。如果核心测试失败，可选择丢弃并重做。
* **数学透明。** BIP-39 算法用纯 Python 在 ~100 行内实现，配套 `docs/BIP39-math.md`
  让你在纸上逐位复算。

### 本项目**不是**什么

* **不是钱包**。不派生私钥、不管 UTXO、不签名交易。拿到 24 词后请**导入**到
  [Sparrow](https://sparrowwallet.com/) / [Electrum](https://electrum.org/) /
  [Bitcoin Core](https://bitcoincore.org/) 或你信任的硬件钱包。
* **不能替代固件更新。** 如果你持有 Coldcard，请**先**更新固件 —— 修复后的
  固件是必要的，否则设备可能用坏 RNG 覆盖你精心准备的种子。**离线**生成、
  **再导入**到修复后的设备。
* **与 Coinkite、Block、Trezor、Ledger、SatoshiLabs 或任何钱包厂商均无关联**。
  词表与算法引用基于 MIT 协议的 BIP-39 规范。
* **不能保证你的种子绝对安全。** 24 词助记词的强度等于生成它的熵的强度。
  本工具帮你**验证**熵，但**最终的审计师是你自己**。

### 一句话总结

> Coldcard 教会整个行业：信任链在熵源处断裂。本项目给你一个
> 小而可读的工具，让**你**成为那个熵源。

---

## 3. 日本語

### このプロジェクトが生まれた理由

**2026 年 7 月**、Bitcoin コミュニティは、史上最も「恥ずかしい」ハードウェア
ウォレットの失敗の一つに直面しました。
[ **Coldcard の乱数生成器（RNG）脆弱性**](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/) です。

* **何が起きたか。** 2021 年 3 月 17 日にリリースされたファームウェア
  **v4.0.1** において、`MICROPY_HW_ENABLE_RNG = 0` という 1 行の設定と、
  マクロの**値**ではなく**存在**のみをチェックする条件分岐により、
  ウォレットのシード生成器がハードウェア TRNG ではなく
  `pyb_rng_yasmarang`（**ソフトウェア疑似乱数生成器**）を呼び出すように
  なっていました。
* **どれほど潜伏していたか。** 2021 年 3 月に出荷され、**2026 年 7 月 30 日**
  に公開されるまで——**5 年以上**。
* **影響を受けたデバイス。** Coldcard **Mk2 / Mk3 / Mk4 / Mk5 / Q** の、
  v4.0.1 以降のすべてのファームウェア。（TAPSIGNER / OPENDIME / SATSCARD は
  影響を受けず。）パッチ公開日まで、影響を受けた全デバイスは**依然として**
  低エントロピーのシードを生成し続けていました。
* **有効エントロピーの低下**。
  * Mk3：約 **40 bit**（目標 128 bit）。
  * Mk4 / Mk5 / Q：約 **72 bit**。
  * 40 bit ≈ 1 兆通り。**現代の GPU クラスターなら数時間で全探索可能**。
* **被害。** **2026 年 7 月 30–31 日**、少なくとも **15 名の独立攻撃者**が
  連携して **4 波**の攻撃を仕掛け、およそ **7,300 アドレス**から合計
  約 **1,367 BTC**（当時のレートで**約 1.1 億ドル**）を流出させました。
  第 1 波は Coinkite 公式警告の**30 時間前**に始まり、約 500 ウォレット
  （約 594 BTC）をわずか 30 分で空にしました。
* **AI による発見。** Reddit の開発者が Claude Code で公開ファームウェアを
  スキャンし、**わずか 8 分で脆弱性を再現**しました——5 年間も「公開の場」に
  隠れていたことを裏付けました。
* **Coinkite 公式の事後推奨**は、**物理サイコロを少なくとも 50 回振って**
  真の乱数を付加し、修正済みデバイスで**新規シードを再生成**することです。

参考資料：[Coinkite アドバイザリ](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/)、
[Block 技術解説](https://engineering.block.xyz/blog/predictable-rng-fallback-and-32-bit-reseed-in-coldcard-firmware)、
[Galaxy Digital オンチェーン分析](https://www.galaxy.com/)、
[BleepingComputer 報道](https://www.bleepingcomputer.com/news/security/coldcard-wallet-rng-flaw-likely-linked-to-88-million-bitcoin-theft/)。

### 教訓：「オフライン」≠「安全」

Coldcard 事件は、3 つの安心神話を同時に破壊しました。

1. **「ハードウェアウォレットは構造的に安全」**——違います。シードは
   ソフトウェアであり、ソフトウェアにはバグがあります。
2. **「オープンソースだから安全」**——原則的にはそうですが、Coldcard の
   ファームウェアは 5 年間ずっと GitHub にあったのに、誰も気づきませんでした。
3. **「ファームウェアを更新すれば良い」**——できません。パッチは**今後**の
   生成を修正するだけで、既に作られてしまった壊れたシードは**永久に**壊れた
   ままです。**修正済みデバイスでシードを再生成し、資金を移動する**以外に
   治療法はありません。

より深い教訓は、**いかなるベンダー——どれだけ有名でも——あなたの財産を守る
エントロピーの責任を負えない**ということです。**完全に自分で検証できる
信頼仮定は、乱数源そのもの**だけです。

### Coldcard を踏まえて、本プロジェクトは何であるか

この教訓に基づき、本リポジトリは、**Coldcard ユーザーが彼らのデバイスから
得られなかった性質**を満たすツールを提供します。

* **ゼロ依存。** Python 標準ライブラリのみ。**実行前に全行を読み通せます**。
* **構造的にオフライン。** `interactive` サブコマンドは**ディスクを読まず、
  書きません**。収集したエントロピーはプロセスメモリにのみ存在し、
  ターミナルを閉じれば消去されます。
* **人間が検証可能なエントロピー源。** コイン、サイコロ、カードを切る——
  いずれも物理過程です。自分で実験を監査して、源が公平だと納得できます。
* **NIST SP 800-22 品質検査。** 256 ビットを集めた後、ツールは 8 件の
  統計テスト（頻度、ラン、最長ラン、自己相関、パターン検出 + 補助 3 件）を
  実行し、健全か報告します。コアテストに失敗すれば、エントロピーを破棄して
  再実行できます。
* **数学的に透明。** BIP-39 アルゴリズムは ~100 行の純粋 Python で実装し、
  `docs/BIP39-math.md` で紙の上でも 1 ステップずつ検証可能。

### 本プロジェクトは何**でない**か

* **ウォレットではありません**。鍵派生、UTXO 管理、署名を行いません。
  24 語のニーモニックを手に入れたら、[Sparrow](https://sparrowwallet.com/) /
  [Electrum](https://electrum.org/) / [Bitcoin Core](https://bitcoincore.org/)、
  あるいは信頼できるハードウェアウォレットに**インポート**してください。
* **ファームウェア更新の代替ではありません**。Coldcard をお持ちなら、
  まず**ファームウェアを更新**してください。修正後のファームウェアは
  必要条件であり、そうでないとデバイスがあなたの良いエントロピーを
  壊れた RNG で上書きする可能性があります。**オフラインで生成**してから
  修正後のデバイスに**インポート**してください。
* **Coinkite、Block、Trezor、Ledger、SatoshiLabs、その他いかなるウォレット
  ベンダーとも無関係**です。単語リストとアルゴリズムの参照は、MIT ライセンス
  の BIP-39 仕様に基づきます。
* **シードの安全性を保証するものではありません**。24 語のニーモニックの強度は
  生成したエントロピーの強度と同じです。本ツールはエントロピーの**検証**
  を支援しますが、**最終的な監査人はあなた自身**です。

### まとめ

> Coldcard は業界全体に、乱数源で信頼鎖が崩壊することを教えました。
> 本プロジェクトは、小さく読めるツールで、**あなた自身**がその乱数源に
> なる手段を提供します。

---

## 4. 한국어

### 이 프로젝트가 존재하는 이유

**2026 년 7 월**, Bitcoin 커뮤니티는 하드웨어 지갑 역사상 가장
**당황스러운 공개 실패** 중 하나를 겪었습니다.
[ **Coldcard 난수 생성기 (RNG) 취약점**](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/) 입니다.

* **무슨 일이 있었나.** 2021 년 3 월 17 일에 출시된 펌웨어 **v4.0.1** 에서,
  `MICROPY_HW_ENABLE_RNG = 0` 한 줄 설정과 매크로의 **값**이 아닌
  **존재**만 확인하는 조건 분기로 인해, 지갑 시드 생성기가 하드웨어 TRNG
  가 아닌 `pyb_rng_yasmarang` (**소프트웨어 의사난수 생성기**) 를
  호출하게 되었습니다.
* **얼마나 잠복했나.** 2021 년 3 월에 출시되어 **2026 년 7 월 30 일**에
  공개될 때까지 — **5 년 이상**.
* **영향받은 디바이스.** Coldcard **Mk2 / Mk3 / Mk4 / Mk5 / Q** 의
  v4.0.1 이후 모든 펌웨어. (TAPSIGNER / OPENDIME / SATSCARD 는 영향 없음.)
  패치일까지 영향받은 모든 기기는 **여전히** 낮은 엔트로피 시드를
  생성하고 있었습니다.
* **유효 엔트로피 감소**.
  * Mk3: 약 **40 bit** (목표 128 bit).
  * Mk4 / Mk5 / Q: 약 **72 bit**.
  * 40 bit ≈ 1 조 가지. **현대 GPU 클러스터가 수 시간이면 전수조사 가능**.
* **피해.** **2026 년 7 월 30–31 일**, 최소 **15 명의 독립 공격자**가
  **4 차**에 걸친 공격을 조율하여 약 **7,300 개** 취약 주소에서
  약 **1,367 BTC** (당시 환율로 **약 1.1 억 달러**) 를 인출했습니다.
  1 차 공격은 Coinkite 공식 경고 **30 시간 전**에 시작되어 30 분 만에
  ~500 개 지갑 (~594 BTC) 을 비웠습니다.
* **AI 지원 발견.** 한 Reddit 개발자가 Claude Code 로 공개 펌웨어를
  스캔하여 **단 8 분 만에** 취약점을 재현했습니다 — 5 년간 "공개된 곳"에
  숨어 있었다는 증거.
* **Coinkite 공식 사후 권고**: **물리 주사위를 최소 50 회 굴려** 진짜
  난수를 추가하고, 패치된 디바이스에서 **새 시드를 재생성**할 것.

출처: [Coinkite 권고](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/),
[Block 기술 분석](https://engineering.block.xyz/blog/predictable-rng-fallback-and-32-bit-reseed-in-coldcard-firmware),
[Galaxy Digital 온체인 분석](https://www.galaxy.com/),
[BleepingComputer 기사](https://www.bleepingcomputer.com/news/security/coldcard-wallet-rng-flaw-likely-linked-to-88-million-bitcoin-theft/).

### 교훈: "오프라인" ≠ "안전"

Coldcard 사건은 세 가지 안일한 신화를 동시에 무너뜨렸습니다.

1. **"하드웨어 지갑은 구조적으로 안전"** — 아닙니다. 시드는 결국
   소프트웨어이며, 소프트웨어에는 버그가 있습니다.
2. **"오픈소스 펌웨어가 더 안전"** — 원칙적으로는 그렇지만, 실제로는
   Coldcard 펌웨어가 5 년 동안 GitHub 에 있었는데 아무도 발견하지 못했습니다.
3. **"펌웨어 업데이트만 하면 된다"** — 안 됩니다. 패치는 **앞으로**의
   생성을 고칠 뿐, 이미 만들어진 깨진 시드는 **영원히** 깨져 있습니다.
   **패치된 디바이스에서 시드를 새로 생성하고 자금을 이동**하는 것만이
   유일한 치료법입니다.

더 깊은 교훈은 **어떤 벤더도 — 아무리 유명해도 — 당신의 자산을 보호하는
엔트로피의 책임을 질 수 없다**는 것입니다. **완전히 스스로 검증할 수 있는
신뢰 가정은 난수원 그 자체**입니다.

### Coldcard 이후, 이 프로젝트는 무엇인가

이 교훈을 바탕으로, 본 저장소는 **Coldcard 사용자가 자신의 디바이스에서
얻을 수 없었던 성질**을 충족하는 도구를 제공합니다.

* **제로 의존성.** Python 표준 라이브러리만 사용. **실행 전에 모든 줄을
  읽을 수 있습니다.**
* **구조적으로 오프라인.** `interactive` 서브커맨드는 **디스크를 읽지도
  쓰지도 않습니다.** 수집한 엔트로피는 프로세스 메모리에만 존재하며,
  터미널을 닫으면 사라집니다.
* **인간이 검증할 수 있는 엔트로피 원천.** 동전, 주사위, 카드 셔플 — 모두
  물리적 과정입니다. 실험 과정을 직접 감사하여 원천이 공정하다고
  확신할 수 있습니다.
* **NIST SP 800-22 품질 검사.** 256 비트를 수집한 후, 도구는 8 가지 통계
  테스트 (빈도, 런, 최장 런, 자기상관, 패턴 탐지 + 보조 3 항목) 를 실행하여
  샘플의 건재성을 알려줍니다. 핵심 테스트가 실패하면 엔트로피를 폐기하고
  재실행할 수 있습니다.
* **수학적으로 투명.** BIP-39 알고리즘은 ~100 줄의 순수 Python 으로
  구현되었으며, `docs/BIP39-math.md` 가 종이 위에서도 한 단계씩 검증할 수
  있도록 안내합니다.

### 이 프로젝트는 무엇이 **아닌가**

* **지갑이 아닙니다**. 키 파생, UTXO 관리, 트랜잭션 서명을 하지 않습니다.
  24 단어 니모닉을 받으면 [Sparrow](https://sparrowwallet.com/) /
  [Electrum](https://electrum.org/) / [Bitcoin Core](https://bitcoincore.org/) 또는
  신뢰할 수 있는 하드웨어 지갑에 **가져오기** 하세요.
* **펌웨어 업데이트를 대체하지 않습니다.** Coldcard 를 보유하고 있다면,
  먼저 **펌웨어를 업데이트** 하세요. 패치된 펌웨어는 필수 조건이며,
  그렇지 않으면 디바이스가 당신이 정성껏 준비한 엔트로피를 깨진 RNG 로
  덮어쓸 수 있습니다. **오프라인에서 생성**한 다음 패치된 디바이스에
  **가져오기** 하세요.
* **Coinkite, Block, Trezor, Ledger, SatoshiLabs 또는 기타 지갑 벤더와
  무관합니다.** 단어 목록과 알고리즘 참조는 MIT 라이선스의 BIP-39 명세를
  기반으로 합니다.
* **시드의 절대적 안전을 보장하지 않습니다.** 24 단어 니모닉의 강도는
  그것을 생성한 엔트로피의 강도와 같습니다. 이 도구는 엔트로피 **검증**을
  도와주지만, **최종 감사인은 당신 자신**입니다.

### 한 줄 요약

> Coldcard 는 업계 전체에 신뢰 사슬이 엔트로피 원천에서 끊어진다는 것을
> 가르쳤습니다. 이 프로젝트는 작고 읽을 수 있는 도구로 **당신 자신**이
> 그 엔트로피 원천이 될 수 있는 수단을 제공합니다.