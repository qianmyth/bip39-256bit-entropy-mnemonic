# BIP-39 256 位熵助记词生成器（24 词 / Bitcoin 标准）

> **一个完整、可审计、零依赖的 BIP-39 实现，目标熵 256 位（24 词助记词）。**
>
> 离线优先 · 可逐行审计 · 小白也能上手

**Languages:** [English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md)

**运行时本地化：** CLI / 交互模式会自动从 `LANG` / `LC_ALL` / `BIP39_LANG`
环境变量中识别语言，并相应地以英文 / 简体中文 / 日本語 输出提示。其他 locale
一律回落为英文。也可通过 `BIP39_LANG=ja python3 bip39_offline_v5.py ...` 强制指定。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-BIP--39%20vectors%20passing-brightgreen.svg)](docs/BIP39-math.md)

---

## 为什么做这个？

**2026 年 7 月**，比特币社区经历了硬件钱包史上**最尴尬的一次公开失败** —— [Coldcard 随机数生成器（RNG）漏洞](https://blog.coinkite.com/coldcard-mk3-seed-generation-warning/)。

2021 年 3 月 17 日发布的固件 v4.0.1 中，一行配置 `MICROPY_HW_ENABLE_RNG = 0` 配合一段只判断"宏**是否存在**"而非"宏**值**是什么"的条件分支，导致钱包种子生成函数调用了 MicroPython 的 `pyb_rng_yasmarang` —— 一个**软件伪随机数生成器（PRNG）**，而非设备内置的硬件真随机数发生器（TRNG）。这个 bug 在 GitHub 上整整**潜伏了 5 年**才被发现。

实际损失触目惊心：

- **Mk3** 有效熵从 128 bit 跌到 **~40 bit**（约 1 万亿种可能，现代 GPU 集群**几小时**就能穷举完）
- **Mk4 / Mk5 / Q** 跌到 **~72 bit**
- **2026 年 7 月 30–31 日**，至少 **15 个独立攻击者**协调发起 **4 波攻击**，从约 **7,300 个**脆弱地址中扫走约 **1,367 BTC**（折合 **8,800 万–1.11 亿美元**）
- **第一波** 仅用 30 分钟就清空了 ~500 个钱包，**早于 Coinkite 官方公告**整整 30 个小时
- 一位 Reddit 开发者用 Claude Code 在公开固件上扫描，**仅 8 分钟**就复现了这个潜伏 5 年的漏洞

Coldcard 事件一次性戳穿了三个让人安心的迷信：

1. **"硬件钱包天生安全。"** 错。种子终究是软件生成的，而软件有 bug。
2. **"开源固件更安全。"** 原则上对，但实践中 Coldcard 固件一直挂在 GitHub 上，这个 bug 在社区审阅下**活了五年**。
3. **"升级固件就行。"** 不行。补丁只修复**今后**生成的种子；已经用坏 RNG 生成的种子**永远**是坏的。唯一正确做法是**在已修复设备上重新生成种子，并迁移资金**。

更深层的教训是：**没有任何厂商——无论多有名——能对保护你财产的熵源负责**。唯一你能完全验证的信任假设，就是**随机源本身**。

这个项目正是对这一教训的回应：在断网的电脑上手动生成助记词，**每一行代码都摆在面前**。

它只做一件事——把 **256 位熵** 安全地变成 **24 词 BIP-39 标准助记词**，并且：

- ✅ 算法与 Trezor、Ledger、MetaMask、Electrum、Sparrow、BlueWallet 完全兼容
- ✅ 256 位熵（24 词）= 任何主流硬件钱包的默认强度
- ✅ 零运行依赖（只用到 Python 标准库）
- ✅ 离线模式**不读盘、不写盘**，熵仅存在于进程内存
- ✅ 内置 8 项 NIST SP 800-22 熵质量检查（核心 5 项 + 辅助 3 项）
- ✅ 支持骰子、硬币、扑克牌、CSV 表格等多种熵来源
- ✅ 不会发起任何网络请求
- ✅ 运行时自动识别语言（English / 简体中文 / 日本語）

---

## 项目结构

```
bip39-256bit-entropy-mnemonic/
├── README.md                  ← 英文主版
├── README.zh-CN.md            ← 本文件（中文）
├── README.ja.md               ← 日本語
├── HOWTO-dice.md              ← 骰子生成完整教程
├── BACKGROUND.md              ← 项目背景：Coldcard 2026 漏洞事件
├── SECURITY.md                ← 威胁模型 & 最佳实践
├── LICENSE                    ← MIT
├── english.txt                ← BIP-39 官方 2048 词表
├── bip39_offline_v5.py        ← 全部功能都在这一个文件里（1470 行）
├── examples/
│   ├── demo_zero_entropy.csv  ← 输入后输出 "abandon…art"
│   └── example_full.csv       ← 一个非零熵示例
├── templates/
│   └── blank_template.csv     ← 空白模板，开始收集熵
└── docs/
    └── BIP39-math.md          ← 算法逐步可视化讲解
```

---

## 快速开始（30 秒上手）

```bash
# 1. 在一台 永远没上过网 的电脑上 clone（或者下载 zip 包）
git clone https://github.com/qianmyth/bip39-256bit-entropy-mnemonic.git
cd bip39-256bit-entropy-mnemonic

# 2. 跑一下 demo CSV（熵全为 0 → 输出著名的 "abandon × 23, art"）
python3 bip39_offline_v5.py generate examples/demo_zero_entropy.csv

# 3. 跑测试套件，确认工具链没问题
python3 -m unittest discover -s tests -v
```

确认 demo 工作之后：

1. 复制 `templates/blank_template.csv` 到 U 盘，插到离线电脑；
2. 在离线电脑上用表格软件打开，逐格填入熵（详见下文）；
3. 执行 `python3 bip39_offline_v5.py generate my_entropy.csv`；
4. **打印**结果，**手抄**到纸上，**销毁**电脑里的所有文件。

---

## 安装

不需要安装任何东西，只要 Python ≥ 3.7。

```bash
git clone https://github.com/qianmyth/bip39-256bit-entropy-mnemonic.git
cd bip39-256bit-entropy-mnemonic
python3 -m unittest discover -s tests    # 可选：验证脚本
```

如果想直接读取 macOS Numbers 文件：

```bash
pip install numbers-parser    # 在联网电脑上装一次，然后把脚本拷到离线机
```

---

## 详细用法

### 方法 A：掷骰子（最推荐 / 纯人力）

详见 [`HOWTO-dice.md`](HOWTO-dice.md)。简版：

```bash
# 把 100 次掷骰子的结果（每行一个 1~6）写入 rolls.txt：
#   4
#   6
#   1
#   3
#   ...

python3 bip39_offline_v5.py from-dice rolls.txt
```

脚本会打印 32 字节熵 + 24 词助记词。**100 颗公平的 6 面骰 ≈ 258.5 比特熵，足够用。**

### 方法 B：手工填表

打开 `templates/blank_template.csv`：

|          | c1 | c2 | c3 | … | c11 |
|----------|----|----|----|---|-----|
| group1   | 0  | 0  | 0  | … | 0   |
| …        | …  | …  | …  | … | …   |
| group24  | 0  | 0  | 0  |   |     |

- 把 24 行 × 11 列共 256 个格子手动填成 0 或 1。
- 0 = 不填 / 0 / 空；1 = 标记 / 1。
- 第 24 组只需要填 3 列。

填好后执行：

```bash
python3 bip39_offline_v5.py generate my_entropy.csv
```

输出会一步步展示：
```
24 组二进制  →  256 位熵  →  SHA-256  →  8 位校验和  →  264 位
             →  24 段 × 11 位  →  十进制索引  →  24 个单词
```

### 方法 C：校验已有的助记词

```bash
# 校验
python3 bip39_offline_v5.py validate "abandon abandon ... art"
# → checksum: VALID ✓

# 同时显示 512 位种子（用 TREZOR passphrase 演示）
python3 bip39_offline_v5.py validate --show-seed --passphrase TREZOR \
    "abandon abandon ... art"
# → seed (BIP-39, passphrase='TREZOR'): bda8…cc8
```

### 方法 D：作为 Python 库调用

```python
import bip39_offline_v5 as bip39

# 从骰子生成 256 位熵
entropy = bip39.dice_rolls_to_entropy([3, 5, 6, 1, 2, 4, ...])

# 生成助记词
mnemonic = bip39.entropy_to_mnemonic(entropy)

# 校验
assert bip39.validate_mnemonic(mnemonic)

# 派生种子（wallet 真正使用的 64 字节）
seed = bip39.mnemonic_to_seed(mnemonic, passphrase="optional-passphrase")
```

---

## 算法一览

```
 ┌──────────────────────────────────────────────────────────────────────┐
 │  256 位熵   ─→   SHA-256   ─→   取首 8 位  =  8 位校验和              │
 │                                                                      │
 │  (256 位) ++ (8 位)  =  264 位                                        │
 │                                                                      │
 │  切成 24 段 × 11 位  ─→  24 个 0~2047 的索引                          │
 │                                                                      │
 │  索引 → english.txt[索引]  =  24 个英文单词                           │
 └──────────────────────────────────────────────────────────────────────┘
```

可视化版本见 `docs/BIP39-math.md`。

---

## 测试

```bash
python3 -m unittest discover -s tests -v
```

应输出 **12/12 OK**。其中 4 组向量直接来自
[`trezor/python-mnemonic/vectors.json`](https://github.com/trezor/python-mnemonic/blob/master/vectors.json)，
确保种子与 Trezor、Ledger 完全一致。

---

## 安全提醒（请务必阅读）

1. **必须在一台永不联网的电脑上运行**——哪怕只是临时连一下网，都有可能中键盘记录 / 截屏木马。推荐：Tails 启动盘 + 从未联网的机器。
2. **核对校验和**——脚本会打印 SHA-256 校验和，肉眼对比，确保和第二个独立实现（[`iancoleman/bip39`](https://github.com/iancoleman/bip39) 离线版）一致。
3. **强烈建议加 BIP-39 passphrase（第 25 个词）**——不加，捡到 24 词就等于拿走你的钱；加了，忘了也救不回来。要分开保管。
4. **大额资金，熵源要双备份**（比如既掷骰子又翻硬币，互相校验）。
5. **永远不要在联网电脑上输入真实助记词**。`--show-seed` 是调试功能，输出即作废。

完整威胁模型见 [`SECURITY.md`](SECURITY.md)。

---

## 许可证

MIT —— 见 [LICENSE](LICENSE)。

`english.txt` 来自 BIP-39 官方规范，同样是 MIT 协议。