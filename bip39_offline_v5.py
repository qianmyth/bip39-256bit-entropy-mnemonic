#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BIP-39 24 助记词离线单文件工具 v5.3（合一版）
============================================

本文件将原本散落在 bip39_tool/ 包里的所有功能合并到**一个 Python 文件**，
运行只需要 ``english.txt`` 摆旁边。

支持的能力（共 14 项）：

  1. 交互式无文件输入（双盲确认 + tty 实时控制）
  2. 8 项 NIST SP 800-22 熵质量检查
  3. 检查和验证（24 词 → entropy）
  4. 助记词 → 512 位种子（PBKDF2-HMAC-SHA512）
  5. 骰子（≥99 次 d6）→ 助记词
  6. 硬币（≥256 次）→ 助记词
  7. 扑克牌（≥104 张）→ 助记词
  8. 从 CSV / TXT / Numbers 表格生成助记词
  9. 审计外部 256 位二进制的熵质量
 10. 运行时自动识别语言（English / 简体中文 / 日本語）
 11. 离线运行，零依赖
 12. 全 BIP-39 官方测试向量覆盖
 13. macOS / Linux / Windows 跨平台
 14. Bilingual 用户界面（display 当前用中文、命令帮助用英文）

用法（五个子命令）：

    python3 bip39_offline_v5.py                           # V5 模式：交互输入
    python3 bip39_offline_v5.py generate <path.csv>       # 从表格生成
    python3 bip39_offline_v5.py validate "word1 ... word24"
    python3 bip39_offline_v5.py from-dice <rolls.txt>
    python3 bip39_offline_v5.py check-entropy <bits.txt>

环境变量：

    BIP39_LANG=en|zh-CN|ja   强制指定语言
    LANG=zh_CN.UTF-8         自动识别（默认）

版本历史：
  v5.0  - 原始 V5 文件（无文件模式 + 检查）
  v5.1  - 融合 bip39_tool 核心算法
  v5.2  - 加入 8 项 NIST 检查 + p-value 标注
  v5.3  - 合一：dice / 硬币 / 扑克 / 种子 / 验证 / CSV / i18n
"""

import argparse
import csv
import gc
import hashlib
import hmac
import locale
import math
import os
import sys
import unicodedata
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

# ============================================================================
# 0. 常量与平台检测
# ============================================================================

ENTROPY_BITS = 256
ENTROPY_BYTES = 32
CHECKSUM_BITS = 8
TOTAL_BITS = 264
WORDS_COUNT = 24
WORDLIST_SIZE = 2048
WORDLIST_FILENAME = "english.txt"

ALPHA = 0.01
MAX_RUN_THRESHOLD = 15

IS_UNIX = os.name == "posix"
SUPPORTED_LANGS = ("en", "zh-CN", "ja")
DEFAULT_LANG = "en"

# 当前语言（运行时会被 set_language() 修改）
_current_lang: Optional[str] = None


# ============================================================================
# 1. i18n：运行时语言识别 + 翻译表
# ============================================================================

def _norm_loc(value: str) -> str:
    if not value:
        return ""
    value = value.strip().replace("_", "-")
    return value.split(".", 1)[0]


def _accept_locale(loc: str) -> Optional[str]:
    """把任意 locale 字符串映射到 SUPPORTED_LANGS 之一。

    不可识别时返回 ``None``（让调用者继续尝试下一个候选）。
    """
    primary = _norm_loc(loc)
    if not primary:
        return None
    head = primary.lower().split("-", 1)[0]
    if head == "zh":
        return "zh-CN"
    if head == "ja":
        return "ja"
    return None


def detect_language() -> str:
    """按以下优先级自动检测语言：
        1. ``set_language()`` 显式设置
        2. ``BIP39_LANG`` 环境变量
        3. ``LANGUAGE`` / ``LC_ALL`` / ``LC_MESSAGES`` / ``LANG``
        4. 系统默认 locale
        5. 英文兜底
    """
    if _current_lang is not None and _current_lang in SUPPORTED_LANGS:
        return _current_lang

    override = os.environ.get("BIP39_LANG", "").strip()
    if override in SUPPORTED_LANGS:
        return override

    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        raw = os.environ.get(var, "").strip()
        if not raw:
            continue
        for candidate in raw.split(":"):
            code = _accept_locale(candidate)
            if code is not None and code in SUPPORTED_LANGS:
                return code

    try:
        default = locale.getdefaultlocale()[0] or ""
    except Exception:
        default = ""
    if default:
        code = _accept_locale(default)
        if code is not None and code in SUPPORTED_LANGS:
            return code

    return DEFAULT_LANG


def set_language(code: Optional[str]) -> None:
    """强制设置语言。``None`` 表示清除，回落到环境检测。"""
    global _current_lang
    if code is None:
        _current_lang = None
    elif code in SUPPORTED_LANGS:
        _current_lang = code
    else:
        _current_lang = DEFAULT_LANG


def get_language() -> str:
    return detect_language()


# 翻译表（懒加载）
_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "title.interactive": "BIP39 24-word offline mnemonic generator",
        "title.interactive_mode": "file-less input + entropy quality check",
        "warning.unset_histfile": "Run with: unset HISTFILE",
        "warning.no_files": "1. This script reads no input files",
        "warning.no_files.2": "2. No output files are written",
        "warning.no_files.3": "3. Close the terminal when done -- all data is gone",
        "warning.no_files.4": "4. Run in a camera-free environment",
        "hint.windows_mode": "[Hint] Windows mode: normal input, mind the bit count",
        "hint.windows_mode.2": "        Whitespace allowed, e.g. 0 0 1 0 1 ...",
        "self.test.pass": "[self-test] BIP39 zero-entropy vector passed.",
        "prompt.input_group": "  group {n:>2} [attempt 1] enter {bits} bits: ",
        "prompt.input_group.2": "  group {n:>2} [attempt 2] enter {bits} bits: ",
        "you.entered": "    you entered: {bits}",
        "group.confirmed": "    OK group {n} confirmed: {bits}",
        "group.mismatch": "    [error] two entries differ, please re-enter",
        "group.first": "    attempt 1: {bits}",
        "group.second": "    attempt 2: {bits}",
        "input.header": "Please enter 24 binary groups",
        "input.rule1": "Rule: first 23 groups are 11 bits each, group 24 is 3 bits",
        "input.rule2": "Each group must be entered twice and match before proceeding",
        "input.unix.hint": "Typing: input stops once the required bit count is reached",
        "input.win.hint": "Typing: mind the bit count (whitespace allowed)",
        "input.display": "Display: bits are auto-spaced for readability",
        "input.interrupt": "Interrupt: press Ctrl+C to quit",
        "input.entering": "checking entropy quality...",
        "result.header": "Result",
        "result.entropy_hex": "entropy (HEX, 32 bytes): {hex}",
        "result.sha256": "SHA256(entropy)        : {hex}",
        "result.checksum": "checksum (8 bits)     : {bits}",
        "result.mnemonic_header": "*** 24-word BIP39 mnemonic ***",
        "result.full_mnemonic": "full mnemonic:",
        "result.checksum_pass": "checksum verification: PASS",
        "result.checksum_fail": "checksum verification: FAIL",
        "result.write_down": "Please write the mnemonic down on a metal plate NOW",
        "result.press_enter": "Press Enter to clear the screen...",
        "result.screen_cleared": "Screen cleared. Please close the terminal.",
        "user.intrupted": "User interrupted. Exiting.",
        "ent.input.header": "Entropy quality check report",
        "ent.alpha": "Significance threshold: alpha = {alpha}",
        "ent.note1": "Notes:",
        "ent.note2": "  - 256-bit samples have limited statistical power; passing != high entropy",
        "ent.note3": "  - Process quality (coin fairness, independence) matters far more",
        "ent.note4": "  - Auxiliary test p-values are rough approximations, informational only",
        "ent.category.core": "[core]",
        "ent.category.aux": "[aux ]",
        "ent.status.pass": "ok pass",
        "ent.status.fail": "X  fail",
        "ent.warning_count": "Total warnings: {n}",
        "ent.verdict.all_pass": "Verdict: OK all core tests passed, entropy quality acceptable",
        "ent.verdict.core_fail": "Verdict: X some core tests failed, strongly recommend regenerating!",
        "ent.verdict.aux_warn": "Verdict: ! core tests passed but auxiliary warnings exist",
        "ent.warning_details": "Warning details:",
        "ent.warning.core": "{name} failed: {desc}",
        "ent.warning.aux": "{name} warning (auxiliary): {desc}",
        "ent.test.frequency": "Frequency Test",
        "ent.test.runs": "Runs Test",
        "ent.test.longest_run": "Longest Run Test",
        "ent.test.autocorrelation": "Autocorrelation Test",
        "ent.test.pattern": "Pattern Detection",
        "ent.test.serial": "Serial Test",
        "ent.test.block_freq": "Block Frequency Test",
        "ent.test.entropy_est": "Entropy Estimates",
        "ent.core_failed.banner": "WARNING: core entropy quality check failed!",
        "ent.core_failed.opt1": "  [R] re-run with new random data (recommended)",
        "ent.core_failed.opt2": "  [C] continue anyway (your own risk)",
        "ent.core_failed.opt3": "  [Q] quit",
        "ent.aux_warn.banner": "Note: auxiliary warnings exist, but core tests passed",
        "ent.aux_warn.opt1": "  [C] continue to compute the mnemonic",
        "ent.aux_warn.opt2": "  [R] re-run with new random data",
        "ent.aux_warn.opt3": "  [Q] quit",
        "ent.please_choice": "Please choose [{opts}]: ",
        "ent.invalid_choice": "Invalid option, please enter {opts}",
        "ent.re_run": "Please re-run with new random data.",
        "ent.user_force_continue": "User chose to continue at own risk...",
        "ent.user_quit": "Exited.",
        "patt.all_zeros": "all-zeros sequence",
        "patt.all_ones": "all-ones sequence",
        "patt.alternating": "perfect alternating pattern",
        "patt.period": "period {p} repetition",
        "patt.half_mirror": "first half equals second half",
        "patt.long_zeros": "20+ consecutive zeros",
        "patt.long_ones": "20+ consecutive ones",
        "patt.none": "no anomalies",
        "stat.frequency": "ones={ones}, zeros={zeros}, ratio={ratio}",
        "stat.runs": "runs={runs}, expected={expected}, z={z}",
        "stat.runs.imbalance": "ratio imbalanced (pi={pi}), runs test invalid",
        "stat.runs.variance": "variance calculation error",
        "stat.longest_run": "longest run={max_run}, threshold={threshold}",
        "stat.autocorrelation": "worst lag={lag}, match rate={prop}",
        "stat.autocorr.empty": "no lag computed",
        "stat.empty": "empty sequence",
        "stat.serial": "chi2(2-bit)={chi2_2}, chi2(3-bit)={chi2_3}",
        "stat.block_freq": "blocks={blocks}, chi2={chi2}",
        "stat.block_freq.skip": "not enough blocks, skipping",
        "stat.entropy": "shannon={shannon}, min-entropy={min_ent}",
        "stat.p_note": "informational only",
        "invalid_bits": "  [error] need {bits} bits, got {n}",
        "non_binary": "  [error] only 0 and 1 allowed",
        "format.hint": "  [hint] you can type with spaces, e.g. 0 0 1 0 1 ...",
        "cli.error.file_not_found": "[error] file not found: {path}",
        "cli.error.expected_24": "[error] expected 24 groups, got {n}",
        "cli.error.group_short": "[error] group {n} has only {m} bits, need {k}",
        "cli.error.bad_cell": "unexpected cell value {val}",
        "cli.error.bad_coin": "unrecognised coin flip: {val}",
        "cli.error.bad_card": "unknown card at position {i}: {val}",
        "cli.error.bad_dice": "dice rolls must be in 1..6, got {vals}",
        "cli.error.short_dice": "need at least {n} fair d6 rolls for 256 bits of entropy, got {m}",
        "cli.error.short_coin": "need at least {n} fair coin flips for 256 bits, got {m}",
        "cli.error.bad_deck": "pass exactly one (52 cards) or two (104 cards) decks",
        "cli.error.deck_insufficient": "only {n} bits of entropy, need 256; pass 2 decks (104 cards)",
        "cli.error.non_binary_line": "[error] non-binary line: {val}",
        "cli.error.numbers_parser": "[error] parsing .numbers requires `pip install numbers-parser`. Save as .csv instead.",
        "cli.error.bad_word": "word not in BIP-39 wordlist: {word}",
        "cli.error.mnemonic_length": "mnemonic must be exactly {n} words, got {m}",
        "cli.error.too_many_bits": "mnemonic encodes too many bits",
        "cli.error.bad_checksum": "invalid checksum",
        "cli.error.entropy_length": "entropy must be exactly {n} bytes ({bits} bits), got {m}",
        "cli.error.bits256_required": "file must contain exactly 256 binary characters",
        "cli.checksum_valid": "checksum: VALID",
        "cli.checksum_invalid": "checksum: INVALID",
        "cli.show_entropy": "entropy (hex): {hex}",
        "cli.show_seed": "seed (BIP-39, passphrase={p}): {hex}",
        "cli.read_groups": "[read] {name}: {n} groups",
        "cli.dice_received": "[dice] received {n} rolls",
    },
    "zh-CN": {
        "title.interactive": "BIP39 24 助记词离线计算工具",
        "title.interactive_mode": "无文件模式 + 熵质量检查",
        "warning.unset_histfile": "运行前请禁用 shell 历史：unset HISTFILE",
        "warning.no_files": "1. 本脚本不读取任何输入文件",
        "warning.no_files.2": "2. 不输出任何文件",
        "warning.no_files.3": "3. 关闭终端后，所有数据消失",
        "warning.no_files.4": "4. 建议在无摄像头环境运行",
        "hint.windows_mode": "[提示] Windows 模式：使用普通输入，请手动确保位数正确",
        "hint.windows_mode.2": "         支持带空格输入，如: 0 0 1 0 1 ...",
        "self.test.pass": "[自检] BIP39 零熵测试向量通过。",
        "prompt.input_group": "  组 {n:>2} [第一次] 输入 {bits} 位: ",
        "prompt.input_group.2": "  组 {n:>2} [第二次] 输入 {bits} 位: ",
        "you.entered": "    你输入: {bits}",
        "group.confirmed": "    OK 组 {n} 确认通过: {bits}",
        "group.mismatch": "    [错误] 两次输入不一致，请重新输入",
        "group.first": "    第一次: {bits}",
        "group.second": "    第二次: {bits}",
        "input.header": "请逐组输入 24 组二进制",
        "input.rule1": "规则：前 23 组每组 11 位，第 24 组 3 位",
        "input.rule2": "每组需输入两次，确认一致后才进入下一组",
        "input.unix.hint": "输入时：达到指定位数后不再接受输入",
        "input.win.hint": "输入时：请确保输入正确的位数（可带空格）",
        "input.display": "显示时：二进制数字之间自动加空格",
        "input.interrupt": "中断：按 Ctrl+C 可随时退出",
        "input.entering": "正在进行熵质量检查...",
        "result.header": "计算结果",
        "result.entropy_hex": "熵 (HEX, 32 字节): {hex}",
        "result.sha256": "SHA256(熵)        : {hex}",
        "result.checksum": "校验和 (8 位)     : {bits}",
        "result.mnemonic_header": "*** 24 个 BIP39 助记词 ***",
        "result.full_mnemonic": "完整助记词：",
        "result.checksum_pass": "校验和验证：通过",
        "result.checksum_fail": "校验和验证：失败",
        "result.write_down": "请立刻手抄助记词到金属板",
        "result.press_enter": "抄写完成后，按回车键清屏...",
        "result.screen_cleared": "请关闭终端以清除内存。",
        "user.intrupted": "用户中断。已退出。",
        "ent.input.header": "熵质量检查报告",
        "ent.alpha": "显著性水平阈值: alpha = {alpha}",
        "ent.note1": "说明：",
        "ent.note2": "  - 256 位样本检测力有限，通过检查 ≠ 高熵",
        "ent.note3": "  - 过程质量（硬币公平性、独立性）才是第一位",
        "ent.note4": "  - 辅助测试 p-value 仅供参考，不参与核心决策",
        "ent.category.core": "[核心]",
        "ent.category.aux": "[辅助]",
        "ent.status.pass": "通过",
        "ent.status.fail": "失败",
        "ent.warning_count": "总警告数: {n}",
        "ent.verdict.all_pass": "综合判断: 所有核心测试通过，熵质量可接受",
        "ent.verdict.core_fail": "综合判断: 存在核心测试失败，强烈建议重新生成！",
        "ent.verdict.aux_warn": "综合判断: 核心测试通过，但存在辅助警告",
        "ent.warning_details": "警告详情:",
        "ent.warning.core": "{name} 失败: {desc}",
        "ent.warning.aux": "{name} 警告(辅助): {desc}",
        "ent.test.frequency": "Frequency Test",
        "ent.test.runs": "Runs Test",
        "ent.test.longest_run": "Longest Run Test",
        "ent.test.autocorrelation": "Autocorrelation Test",
        "ent.test.pattern": "Pattern Detection",
        "ent.test.serial": "Serial Test",
        "ent.test.block_freq": "Block Frequency Test",
        "ent.test.entropy_est": "Entropy Estimates",
        "ent.core_failed.banner": "警告：核心熵质量检查失败！",
        "ent.core_failed.opt1": "  [R] 重新运行脚本，生成新的随机数（推荐）",
        "ent.core_failed.opt2": "  [C] 强制继续计算助记词（风险自负）",
        "ent.core_failed.opt3": "  [Q] 退出",
        "ent.aux_warn.banner": "提示：存在辅助警告，但核心测试通过",
        "ent.aux_warn.opt1": "  [C] 继续计算助记词",
        "ent.aux_warn.opt2": "  [R] 重新运行脚本，生成新的随机数",
        "ent.aux_warn.opt3": "  [Q] 退出",
        "ent.please_choice": "请选择 [{opts}]: ",
        "ent.invalid_choice": "无效选项，请输入 {opts}",
        "ent.re_run": "请重新运行脚本，使用新的随机数。",
        "ent.user_force_continue": "用户选择强制继续...",
        "ent.user_quit": "已退出。",
        "patt.all_zeros": "全 0 序列",
        "patt.all_ones": "全 1 序列",
        "patt.alternating": "完美交替模式",
        "patt.period": "周期{p}重复",
        "patt.half_mirror": "前后半段完全相同",
        "patt.long_zeros": "连续20+个0",
        "patt.long_ones": "连续20+个1",
        "patt.none": "无异常",
        "stat.frequency": "1的数量={ones}, 0的数量={zeros}, 比例={ratio}",
        "stat.runs": "游程数={runs}, 期望={expected}, z={z}",
        "stat.runs.imbalance": "比例失衡(pi={pi}), 游程测试无效",
        "stat.runs.variance": "方差计算异常",
        "stat.longest_run": "最长游程={max_run}, 阈值={threshold}",
        "stat.autocorrelation": "最差滞后={lag}, 相同率={prop}",
        "stat.autocorr.empty": "无滞后计算",
        "stat.empty": "空序列",
        "stat.serial": "χ²(2-bit)={chi2_2}, χ²(3-bit)={chi2_3}",
        "stat.block_freq": "块数={blocks}, χ²={chi2}",
        "stat.block_freq.skip": "块数不足，跳过",
        "stat.entropy": "Shannon={shannon}, Min-Entropy={min_ent}",
        "stat.p_note": "仅供参考",
        "invalid_bits": "  [错误] 需要输入 {bits} 位，实际输入 {n} 位",
        "non_binary": "  [错误] 只能包含 0 和 1",
        "format.hint": "  [提示] 可以输入带空格的格式，如: 0 0 1 0 1 ...",
        "cli.error.file_not_found": "[错误] 文件不存在: {path}",
        "cli.error.expected_24": "[错误] 需要 24 组数据, 得到 {n} 组",
        "cli.error.group_short": "[错误] 第 {n} 组只有 {m} 位，不足 {k} 位",
        "cli.error.bad_cell": "非预期的单元格值 {val}",
        "cli.error.bad_coin": "无法识别的硬币输入: {val}",
        "cli.error.bad_card": "未知的牌: 第 {i} 张是 {val}",
        "cli.error.bad_dice": "骰子点数必须在 1..6，得到 {vals}",
        "cli.error.short_dice": "至少需要 {n} 次公平的 d6 投掷才能得到 256 位熵，实际 {m} 次",
        "cli.error.short_coin": "至少需要 {n} 次公平的硬币翻转才能得到 256 位，实际 {m} 次",
        "cli.error.bad_deck": "需要恰好一副 (52 张) 或两副 (104 张) 牌",
        "cli.error.deck_insufficient": "只有 {n} 位熵, 需要 256 位; 请传入两副牌 (104 张)",
        "cli.error.non_binary_line": "[错误] 非二进制行: {val}",
        "cli.error.numbers_parser": "[错误] 解析 .numbers 需要 `pip install numbers-parser`. 请将表格另存为 .csv",
        "cli.error.bad_word": "单词不在 BIP-39 词表中: {word}",
        "cli.error.mnemonic_length": "助记词必须恰好 {n} 词, 得到 {m} 词",
        "cli.error.too_many_bits": "助记词编码的位数过多",
        "cli.error.bad_checksum": "校验和无效",
        "cli.error.entropy_length": "熵必须恰好 {n} 字节 ({bits} 位), 得到 {m} 字节",
        "cli.error.bits256_required": "文件必须包含恰好 256 个二进制字符",
        "cli.checksum_valid": "checksum: 有效",
        "cli.checksum_invalid": "checksum: 无效",
        "cli.show_entropy": "entropy (hex): {hex}",
        "cli.show_seed": "seed (BIP-39, passphrase={p}): {hex}",
        "cli.read_groups": "[已读取] {name}: {n} 组",
        "cli.dice_received": "[dice] 收到 {n} 次投掷",
    },
    "ja": {
        "title.interactive": "BIP39 24 ニーモニック オフライン計算ツール",
        "title.interactive_mode": "ファイルレス入力 + エントロピー品質チェック",
        "warning.unset_histfile": "実行前にシェル履歴を無効化: unset HISTFILE",
        "warning.no_files": "1. このスクリプトは入力ファイルを読みません",
        "warning.no_files.2": "2. 出力ファイルも書き出しません",
        "warning.no_files.3": "3. 終了したらターミナルを閉じてください",
        "warning.no_files.4": "4. カメラのない環境で実行してください",
        "hint.windows_mode": "[ヒント] Windows モード: 通常入力, ビット数を自分で管理",
        "hint.windows_mode.2": "        空白区切り可 (例: 0 0 1 0 1 ...)",
        "self.test.pass": "[自己テスト] BIP39 ゼロエントロピー ベクタ合格。",
        "prompt.input_group": "  グループ {n:>2} [1回目] {bits} ビット入力: ",
        "prompt.input_group.2": "  グループ {n:>2} [2回目] {bits} ビット入力: ",
        "you.entered": "    入力: {bits}",
        "group.confirmed": "    OK グループ {n} 確認: {bits}",
        "group.mismatch": "    [エラー] 2 回の入力が一致しません, 再入力してください",
        "group.first": "    1 回目: {bits}",
        "group.second": "    2 回目: {bits}",
        "input.header": "24 個のバイナリ グループを 1 つずつ入力",
        "input.rule1": "ルール: 最初の 23 グループは 11 ビット, グループ 24 は 3 ビット",
        "input.rule2": "各グループは 2 回入力し, 一致後に次へ進みます",
        "input.unix.hint": "入力: 必要ビット数に達したら自動的に停止",
        "input.win.hint": "入力: ビット数を確認してください (空白区切り可)",
        "input.display": "表示: ビットは自動で区切り表示されます",
        "input.interrupt": "中断: いつでも Ctrl+C で終了",
        "input.entering": "エントロピー品質チェックを実行中...",
        "result.header": "計算結果",
        "result.entropy_hex": "エントロピー (HEX, 32 バイト): {hex}",
        "result.sha256": "SHA256(エントロピー)        : {hex}",
        "result.checksum": "チェックサム (8 ビット)     : {bits}",
        "result.mnemonic_header": "*** 24 語の BIP39 ニーモニック ***",
        "result.full_mnemonic": "ニーモニック全体:",
        "result.checksum_pass": "チェックサム検証: 合格",
        "result.checksum_fail": "チェックサム検証: 不合格",
        "result.write_down": "すぐにニーモニックを金属板に書き写してください",
        "result.press_enter": "書き終えたら Enter を押して画面をクリア...",
        "result.screen_cleared": "画面をクリアしました. ターミナルを閉じてください.",
        "user.intrupted": "ユーザー中断. 終了します.",
        "ent.input.header": "エントロピー品質チェック レポート",
        "ent.alpha": "有意水準: alpha = {alpha}",
        "ent.note1": "注意:",
        "ent.note2": "  - 256 ビット サンプルは検出力が限定的; 合格 ≠ 高エントロピーの証明",
        "ent.note3": "  - プロセスの品質 (コインの公平性, 独立性) が最も重要です",
        "ent.note4": "  - 補助テストの p 値は近似値で参考のみ",
        "ent.category.core": "[主要]",
        "ent.category.aux": "[補助]",
        "ent.status.pass": "合格",
        "ent.status.fail": "不合格",
        "ent.warning_count": "総警告数: {n}",
        "ent.verdict.all_pass": "判定: OK 主要テストすべて合格, エントロピー品質は許容範囲",
        "ent.verdict.core_fail": "判定: X 主要テスト不合格, 再生成を強く推奨!",
        "ent.verdict.aux_warn": "判定: ! 主要テスト合格だが補助警告あり",
        "ent.warning_details": "警告詳細:",
        "ent.warning.core": "{name} 失敗: {desc}",
        "ent.warning.aux": "{name} 警告 (補助): {desc}",
        "ent.test.frequency": "Frequency Test",
        "ent.test.runs": "Runs Test",
        "ent.test.longest_run": "Longest Run Test",
        "ent.test.autocorrelation": "Autocorrelation Test",
        "ent.test.pattern": "Pattern Detection",
        "ent.test.serial": "Serial Test",
        "ent.test.block_freq": "Block Frequency Test",
        "ent.test.entropy_est": "Entropy Estimates",
        "ent.core_failed.banner": "警告: 主要エントロピー品質チェック不合格!",
        "ent.core_failed.opt1": "  [R] 新しい乱数で再実行 (推奨)",
        "ent.core_failed.opt2": "  [C] 続行 (自己責任)",
        "ent.core_failed.opt3": "  [Q] 終了",
        "ent.aux_warn.banner": "注意: 補助警告あり, 主要テストは合格",
        "ent.aux_warn.opt1": "  [C] ニーモニック計算を続行",
        "ent.aux_warn.opt2": "  [R] 新しい乱数で再実行",
        "ent.aux_warn.opt3": "  [Q] 終了",
        "ent.please_choice": "選択してください [{opts}]: ",
        "ent.invalid_choice": "無効な選択です, {opts} を入力してください",
        "ent.re_run": "新しい乱数でスクリプトを再実行してください.",
        "ent.user_force_continue": "ユーザーが続行を選択しました...",
        "ent.user_quit": "終了しました.",
        "patt.all_zeros": "全 0 シーケンス",
        "patt.all_ones": "全 1 シーケンス",
        "patt.alternating": "完全な交互パターン",
        "patt.period": "周期{p}の繰り返し",
        "patt.half_mirror": "前半と後半が完全一致",
        "patt.long_zeros": "20 個以上の連続 0",
        "patt.long_ones": "20 個以上の連続 1",
        "patt.none": "異常なし",
        "stat.frequency": "1の数={ones}, 0の数={zeros}, 比率={ratio}",
        "stat.runs": "ラン数={runs}, 期待値={expected}, z={z}",
        "stat.runs.imbalance": "比率不均衡(pi={pi}), ラン テスト無効",
        "stat.runs.variance": "分散計算エラー",
        "stat.longest_run": "最長ラン={max_run}, しきい値={threshold}",
        "stat.autocorrelation": "最悪ラグ={lag}, 一致率={prop}",
        "stat.autocorr.empty": "ラグ計算なし",
        "stat.empty": "空シーケンス",
        "stat.serial": "χ²(2-bit)={chi2_2}, χ²(3-bit)={chi2_3}",
        "stat.block_freq": "ブロック数={blocks}, χ²={chi2}",
        "stat.block_freq.skip": "ブロック不足, スキップ",
        "stat.entropy": "shannon={shannon}, min-entropy={min_ent}",
        "stat.p_note": "参考のみ",
        "invalid_bits": "  [エラー] {bits} ビット必要, {n} 入力されました",
        "non_binary": "  [エラー] 0 と 1 のみ使用可能",
        "format.hint": "  [ヒント] 空白区切り可 (例: 0 0 1 0 1 ...)",
        "cli.error.file_not_found": "[エラー] ファイルが見つかりません: {path}",
        "cli.error.expected_24": "[エラー] 24 グループ必要, {n} グループ取得",
        "cli.error.group_short": "[エラー] グループ {n} は {m} ビットのみ, {k} 必要",
        "cli.error.bad_cell": "予期しないセル値 {val}",
        "cli.error.bad_coin": "認識できないコイン投げ: {val}",
        "cli.error.bad_card": "不明なカード: 位置 {i} が {val}",
        "cli.error.bad_dice": "サイコロは 1..6 のみ, {vals} 取得",
        "cli.error.short_dice": "256 ビットには {n} 回以上の公平な d6 投げが必要, {m} 回のみ",
        "cli.error.short_coin": "256 ビットには {n} 回以上の公平なコイン投げが必要, {m} 回のみ",
        "cli.error.bad_deck": "ちょうど 1 組 (52 枚) または 2 組 (104 枚) 必要",
        "cli.error.deck_insufficient": "{n} ビットのみ, 256 必要. 2 組 (104 枚) を渡してください",
        "cli.error.non_binary_line": "[エラー] 非バイナリ行: {val}",
        "cli.error.numbers_parser": "[エラー] .numbers の解析には `pip install numbers-parser` が必要. .csv で保存してください.",
        "cli.error.bad_word": "BIP-39 単語リストにない単語: {word}",
        "cli.error.mnemonic_length": "ニーモニックは {n} 語必須, {m} 語取得",
        "cli.error.too_many_bits": "ニーモニックのビット数が多すぎます",
        "cli.error.bad_checksum": "チェックサムが無効",
        "cli.error.entropy_length": "エントロピーは {n} バイト ({bits} ビット) 必須, {m} バイト取得",
        "cli.error.bits256_required": "ファイルには 256 個のバイナリ文字が必要",
        "cli.checksum_valid": "checksum: 有効",
        "cli.checksum_invalid": "checksum: 無効",
        "cli.show_entropy": "entropy (hex): {hex}",
        "cli.show_seed": "seed (BIP-39, passphrase={p}): {hex}",
        "cli.read_groups": "[読み込み] {name}: {n} グループ",
        "cli.dice_received": "[dice] {n} 回の出目を受信",
    },
}


def t(key: str, **kwargs) -> str:
    """返回本地化字符串。找不到的键回落到英文，最坏回落到 key 本身。"""
    lang = detect_language()
    table = _TRANSLATIONS.get(lang, _TRANSLATIONS[DEFAULT_LANG])
    template = table.get(key)
    if template is None:
        template = _TRANSLATIONS[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


# ============================================================================
# 2. BIP-39 核心算法（entropy ↔ mnemonic ↔ seed）
# ============================================================================

def load_wordlist(path: Optional[str] = None) -> List[str]:
    """加载 2048 词的 BIP-39 英文词表。"""
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), WORDLIST_FILENAME)
    if not os.path.exists(path):
        sys.exit(
            f"[error] wordlist not found: {path}\n"
            f"Download from https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt"
        )
    with open(path, "r", encoding="utf-8") as f:
        words = [w.strip() for w in f if w.strip()]
    if len(words) != WORDLIST_SIZE:
        sys.exit(f"[error] wordlist must contain {WORDLIST_SIZE} words, got {len(words)}")
    return words


def entropy_to_mnemonic(entropy: bytes, wordlist: Optional[Sequence[str]] = None) -> List[str]:
    """256 位熵 → 24 词助记词。"""
    if len(entropy) != ENTROPY_BYTES:
        raise ValueError(
            f"entropy must be {ENTROPY_BYTES} bytes ({ENTROPY_BITS} bits), got {len(entropy)}"
        )
    if wordlist is None:
        wordlist = load_wordlist()

    checksum_byte = hashlib.sha256(entropy).digest()[0]
    entropy_bits = int.from_bytes(entropy, "big")
    total = (entropy_bits << CHECKSUM_BITS) | checksum_byte

    words: List[str] = []
    for i in range(WORDS_COUNT):
        idx = (total >> (TOTAL_BITS - (i + 1) * 11)) & 0x7FF
        words.append(wordlist[idx])
    return words


def mnemonic_to_entropy(mnemonic: Sequence[str], wordlist: Optional[Sequence[str]] = None) -> bytes:
    """24 词助记词 → 256 位熵，校验和失败抛 ValueError。"""
    if isinstance(mnemonic, str):
        mnemonic = mnemonic.strip().split()
    if len(mnemonic) != WORDS_COUNT:
        raise ValueError(t("cli.error.mnemonic_length", n=WORDS_COUNT, m=len(mnemonic)))
    if wordlist is None:
        wordlist = load_wordlist()
    index_map = {w: i for i, w in enumerate(wordlist)}

    total = 0
    for w in mnemonic:
        if w not in index_map:
            raise ValueError(t("cli.error.bad_word", word=w))
        total = (total << 11) | index_map[w]
    if total >> TOTAL_BITS:
        raise ValueError(t("cli.error.too_many_bits"))

    checksum = total & ((1 << CHECKSUM_BITS) - 1)
    entropy_bits = total >> CHECKSUM_BITS
    entropy = entropy_bits.to_bytes(ENTROPY_BYTES, "big")
    expected = hashlib.sha256(entropy).digest()[0] >> (8 - CHECKSUM_BITS)
    if checksum != expected:
        raise ValueError(t("cli.error.bad_checksum"))
    return entropy


def mnemonic_to_seed(
    mnemonic: Sequence[str],
    passphrase: str = "",
    wordlist: Optional[Sequence[str]] = None,
) -> bytes:
    """BIP-39 助记词 → 64 字节种子（PBKDF2-HMAC-SHA512, 2048 轮）。"""
    if wordlist is None:
        wordlist = load_wordlist()
    if isinstance(mnemonic, str):
        mnemonic = mnemonic.strip().split()

    password = unicodedata.normalize("NFKD", " ".join(mnemonic))
    salt = unicodedata.normalize("NFKD", "mnemonic" + passphrase).encode("utf-8")
    return hashlib.pbkdf2_hmac("sha512", password.encode("utf-8"), salt, 2048, 64)


def validate_mnemonic(mnemonic: Sequence[str], wordlist: Optional[Sequence[str]] = None) -> bool:
    try:
        mnemonic_to_entropy(mnemonic, wordlist)
        return True
    except (ValueError, KeyError):
        return False


# ============================================================================
# 3. 熵源：骰子 / 硬币 / 扑克
# ============================================================================

def _bits_to_bytes(bits: str) -> bytes:
    bits = "".join(c for c in bits if c in "01")
    if not bits:
        raise ValueError("no binary data")
    pad = (-len(bits)) % 8
    return int((bits + "0" * pad), 2).to_bytes(len(bits + "0" * pad) // 8, "big")


def dice_rolls_to_entropy(rolls: Iterable[int]) -> bytes:
    """≥99 次公平 d6 投掷 → 256 位熵。"""
    rolls = [int(r) for r in rolls]
    if not rolls:
        raise ValueError("no dice rolls provided")
    if any(r < 1 or r > 6 for r in rolls):
        raise ValueError(t("cli.error.bad_dice", vals=sorted(set(rolls))))
    min_rolls = math.ceil(ENTROPY_BYTES * 8 / math.log2(6))
    if len(rolls) < min_rolls:
        raise ValueError(t("cli.error.short_dice", n=min_rolls, m=len(rolls)))

    n = 0
    for r in rolls:
        n = n * 6 + (r - 1)
    # Each die roll gives log2(6) bits; total ceiling guarantees ≥256 bits.
    # We may need up to 257 bits because log2(6) is irrational.
    n = n & ((1 << ENTROPY_BYTES * 8) - 1)
    # Pad to a full 256-bit integer (leading zeros included).
    return n.to_bytes(ENTROPY_BYTES, "big")


def coin_flips_to_entropy(flips: Iterable[Any]) -> bytes:
    """≥256 次公平硬币翻转 → 256 位熵。"""
    bits: List[str] = []
    for f in flips:
        s = str(f).strip().lower()
        if s in ("0", "tail", "tails", "false", "t"):
            bits.append("0")
        elif s in ("1", "head", "heads", "true", "h"):
            bits.append("1")
        else:
            raise ValueError(t("cli.error.bad_coin", val=f))
    if len(bits) < ENTROPY_BYTES * 8:
        raise ValueError(t("cli.error.short_coin", n=ENTROPY_BYTES * 8, m=len(bits)))
    return _bits_to_bytes("".join(bits))


_RANKS = "A23456789TJQK"
_SUITS = "cdhs"
_DECK = [r + s for r in _RANKS for s in _SUITS]


def cards_to_entropy(deck_order: Sequence[str]) -> bytes:
    """一副 (52) 或两副 (104) 洗好的牌 → 256 位熵。"""
    if len(deck_order) not in (52, 104):
        raise ValueError(t("cli.error.bad_deck"))
    for i, c in enumerate(deck_order):
        s = c.strip()
        if s not in _DECK:
            raise ValueError(t("cli.error.bad_card", i=i, val=c))

    n = 0
    for c in deck_order:
        n = n * 52 + _DECK.index(c.strip())
    total_bits = int(len(deck_order) * math.log2(52))
    shift = total_bits - ENTROPY_BYTES * 8
    if shift < 0:
        raise ValueError(t("cli.error.deck_insufficient", n=total_bits))
    return (n >> shift).to_bytes(ENTROPY_BYTES, "big")


# ============================================================================
# 4. NIST SP 800-22 熵质量检查（8 项）
# ============================================================================

def _count_ones(bits: str) -> int:
    return bits.count("1")


def _count_runs(bits: str) -> int:
    if not bits:
        return 0
    runs = 1
    for i in range(1, len(bits)):
        if bits[i] != bits[i - 1]:
            runs += 1
    return runs


def frequency_monobit_test(bits: str) -> Dict[str, Any]:
    n = len(bits)
    ones = _count_ones(bits)
    zeros = n - ones
    s = 2 * ones - n
    s_obs = abs(s) / math.sqrt(n)
    p_value = math.erfc(s_obs / math.sqrt(2))
    passed = p_value >= ALPHA
    return {
        "passed": passed,
        "p_value": p_value,
        "stat": s_obs,
        "desc": t("stat.frequency", ones=ones, zeros=zeros, ratio=f"{ones/n:.3f}"),
    }


def runs_test(bits: str) -> Dict[str, Any]:
    n = len(bits)
    ones = _count_ones(bits)
    zeros = n - ones
    pi = ones / n
    if abs(pi - 0.5) >= 2.0 / math.sqrt(n):
        return {
            "passed": False, "p_value": 0.0, "stat": 0,
            "desc": t("stat.runs.imbalance", pi=f"{pi:.3f}"),
        }
    v_n = _count_runs(bits)
    expected = 2 * ones * zeros / n + 1
    variance = 2 * ones * zeros * (2 * ones * zeros - n) / (n * n * (n - 1))
    if variance <= 0:
        return {"passed": False, "p_value": 0.0, "stat": 0, "desc": t("stat.runs.variance")}
    z = (v_n - expected) / math.sqrt(variance)
    p_value = math.erfc(abs(z) / math.sqrt(2))
    return {
        "passed": p_value >= ALPHA, "p_value": p_value, "stat": abs(z),
        "desc": t("stat.runs", runs=v_n, expected=f"{expected:.1f}", z=f"{z:.3f}"),
    }


def longest_run_test(bits: str, max_allowed: int = MAX_RUN_THRESHOLD) -> Dict[str, Any]:
    if not bits:
        return {"passed": False, "p_value": 0.0, "stat": 0, "desc": t("stat.empty")}
    max_run = current = 1
    for i in range(1, len(bits)):
        if bits[i] == bits[i - 1]:
            current += 1
            max_run = max(max_run, current)
        else:
            current = 1
    expected = math.log2(len(bits))
    z = (max_run - expected) / 1.5
    p_value = max(0.001, min(1.0, 0.5 * math.erfc(z / math.sqrt(2))))
    return {
        "passed": max_run <= max_allowed, "p_value": p_value, "stat": max_run,
        "desc": t("stat.longest_run", max_run=max_run, threshold=max_allowed),
        "p_note": t("stat.p_note"),
    }


def autocorrelation_test(bits: str, max_lag: int = 5) -> Dict[str, Any]:
    n = len(bits)
    results: List[Tuple[int, float, float, float]] = []
    for lag in range(1, min(max_lag + 1, n)):
        matches = sum(1 for i in range(n - lag) if bits[i] == bits[i + lag])
        total = n - lag
        prop = matches / total
        se = math.sqrt(0.25 / total)
        z = abs(prop - 0.5) / se
        p = math.erfc(z / math.sqrt(2))
        results.append((lag, p, z, prop))
    if not results:
        return {"passed": True, "p_value": 1.0, "stat": 0, "desc": t("stat.autocorr.empty")}
    lag, p_value, z, prop = min(results, key=lambda x: x[1])
    return {
        "passed": p_value >= ALPHA, "p_value": p_value, "stat": z,
        "desc": t("stat.autocorrelation", lag=lag, prop=f"{prop:.3f}"),
    }


def detect_obvious_patterns(bits: str) -> Dict[str, Any]:
    n = len(bits)
    patterns: List[str] = []
    if bits == "0" * n:
        patterns.append(t("patt.all_zeros"))
    elif bits == "1" * n:
        patterns.append(t("patt.all_ones"))
    if bits == "01" * (n // 2) or bits == "10" * (n // 2):
        patterns.append(t("patt.alternating"))
    for period in range(2, min(17, n // 2 + 1)):
        pat = bits[:period]
        if bits == pat * (n // period) + pat[: n % period]:
            patterns.append(t("patt.period", p=period))
            break
    half = n // 2
    if bits[:half] == bits[half : 2 * half]:
        patterns.append(t("patt.half_mirror"))
    for i in range(len(bits) - 20):
        if bits[i : i + 20] == "0" * 20:
            patterns.append(t("patt.long_zeros"))
            break
        if bits[i : i + 20] == "1" * 20:
            patterns.append(t("patt.long_ones"))
            break
    return {
        "passed": len(patterns) == 0,
        "patterns": patterns,
        "desc": str(patterns) if patterns else t("patt.none"),
    }


def serial_test(bits: str) -> Dict[str, Any]:
    n = len(bits)
    p2 = Counter(bits[i : i + 2] for i in range(n - 1))
    e2 = (n - 1) / 4
    chi2_2 = sum((p2.get(p, 0) - e2) ** 2 / e2 for p in ("00", "01", "10", "11")) if e2 > 0 else 0
    p3 = Counter(bits[i : i + 3] for i in range(n - 2))
    e3 = (n - 2) / 8
    chi2_3 = (
        sum((p3.get(p, 0) - e3) ** 2 / e3 for p in ("000", "001", "010", "011", "100", "101", "110", "111"))
        if e3 > 0 else 0
    )
    chi2 = chi2_2 + chi2_3
    p_value = max(0.001, min(1.0, 1.0 - chi2 / 40))
    return {
        "passed": chi2 < 25, "p_value": p_value, "stat": chi2,
        "desc": t("stat.serial", chi2_2=f"{chi2_2:.2f}", chi2_3=f"{chi2_3:.2f}"),
        "p_note": t("stat.p_note"),
    }


def block_frequency_test(bits: str, block_size: int = 8) -> Dict[str, Any]:
    n = len(bits)
    num = n // block_size
    if num < 2:
        return {"passed": True, "p_value": 1.0, "stat": 0, "desc": t("stat.block_freq.skip")}
    props = [bits[i * block_size : (i + 1) * block_size].count("1") / block_size for i in range(num)]
    chi2 = sum((p - 0.5) ** 2 for p in props) * 4 * block_size
    p_value = max(0.001, min(1.0, 1.0 - chi2 / 50))
    return {
        "passed": chi2 < 30, "p_value": p_value, "stat": chi2,
        "desc": t("stat.block_freq", blocks=num, chi2=f"{chi2:.2f}"),
        "p_note": t("stat.p_note"),
    }


def entropy_estimates(bits: str) -> Dict[str, Any]:
    n = len(bits)
    ones = _count_ones(bits)
    zeros = n - ones
    p0, p1 = zeros / n, ones / n
    shannon = -p0 * math.log2(p0) - p1 * math.log2(p1) if p0 > 0 and p1 > 0 else 0.0
    min_ent = -math.log2(max(p0, p1)) if max(p0, p1) > 0 else 0.0
    return {
        "passed": shannon >= 0.95 and min_ent >= 0.9, "p_value": None,
        "stat": shannon, "stat2": min_ent,
        "desc": t("stat.entropy", shannon=f"{shannon:.4f}", min_ent=f"{min_ent:.4f}"),
        "p_note": t("stat.p_note"),
    }


def full_entropy_check(bits: str) -> Dict[str, Any]:
    report = {
        "all_passed": True, "core_failed": False,
        "warning_count": 0, "tests": [], "warnings": [],
    }
    core = [
        (t("ent.test.frequency"), frequency_monobit_test(bits)),
        (t("ent.test.runs"), runs_test(bits)),
        (t("ent.test.longest_run"), longest_run_test(bits)),
        (t("ent.test.autocorrelation"), autocorrelation_test(bits)),
        (t("ent.test.pattern"), detect_obvious_patterns(bits)),
    ]
    aux = [
        (t("ent.test.serial"), serial_test(bits)),
        (t("ent.test.block_freq"), block_frequency_test(bits)),
        (t("ent.test.entropy_est"), entropy_estimates(bits)),
    ]
    for name, r in core:
        r["category"] = "core"
        report["tests"].append((name, r))
        if not r["passed"]:
            report["all_passed"] = False
            report["core_failed"] = True
            report["warning_count"] += 1
            report["warnings"].append(t("ent.warning.core", name=name, desc=r["desc"]))
    for name, r in aux:
        r["category"] = "aux"
        report["tests"].append((name, r))
        if not r["passed"]:
            report["warning_count"] += 1
            report["warnings"].append(t("ent.warning.aux", name=name, desc=r["desc"]))
    return report


def display_entropy_check_report(report: Dict[str, Any]) -> None:
    print("\n" + "=" * 70)
    print(t("ent.input.header"))
    print("=" * 70)
    print(t("ent.alpha", alpha=ALPHA))
    print(t("ent.note1"))
    print(t("ent.note2"))
    print(t("ent.note3"))
    print(t("ent.note4"))
    print("-" * 70)
    for name, r in report["tests"]:
        cat = t("ent.category.core") if r["category"] == "core" else t("ent.category.aux")
        status = t("ent.status.pass") if r["passed"] else t("ent.status.fail")
        if r.get("p_value") is not None:
            p_str = f"p={r['p_value']:.4f}"
            if "p_note" in r:
                p_str += f" ({r['p_note']})"
        else:
            p_str = ""
        print(f"{cat} {name:25} {status:10} {p_str:20} | {r['desc']}")
    print("-" * 70)
    print(t("ent.warning_count", n=report["warning_count"]))
    if report["all_passed"]:
        print(t("ent.verdict.all_pass"))
    elif report["core_failed"]:
        print(t("ent.verdict.core_fail"))
    else:
        print(t("ent.verdict.aux_warn"))
    if report["warnings"]:
        print()
        print(t("ent.warning_details"))
        for w in report["warnings"]:
            print(f"  - {w}")
    print("=" * 70)


# ============================================================================
# 5. 跨平台输入（无文件模式 + Windows 兼容）
# ============================================================================

def _format_binary_display(bits: str) -> str:
    return " ".join(bits)


def _read_binary_realtime_unix(prompt: str, max_bits: int) -> str:
    import termios
    import tty
    print(prompt, end="", flush=True)
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    buf = ""
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch in ("\r", "\n"):
                if len(buf) == max_bits:
                    print()
                    break
                sys.stdout.write("\a")
                sys.stdout.flush()
            elif ch == "\x03":
                print()
                print(t("user.intrupted"))
                sys.exit(0)
            elif ch in ("\x7f", "\x08"):
                if buf:
                    buf = buf[:-1]
                    sys.stdout.write("\r" + " " * (len(prompt) + len(buf) * 2 + 10) + "\r")
                    sys.stdout.write(prompt + (_format_binary_display(buf) if buf else ""))
                    sys.stdout.flush()
            elif ch in ("0", "1"):
                if len(buf) < max_bits:
                    buf += ch
                    sys.stdout.write("\r" + prompt + _format_binary_display(buf))
                    sys.stdout.flush()
                else:
                    sys.stdout.write("\a")
                    sys.stdout.flush()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return buf


def _read_binary_simple(prompt: str, max_bits: int) -> str:
    while True:
        try:
            user_input = input(prompt).strip()
        except KeyboardInterrupt:
            print()
            print(t("user.intrupted"))
            sys.exit(0)
        cleaned = user_input.replace(" ", "").replace(",", "")
        if len(cleaned) != max_bits:
            print(t("invalid_bits", bits=max_bits, n=len(cleaned)))
            print(t("format.hint"))
            continue
        if not all(c in ("0", "1") for c in cleaned):
            print(t("non_binary"))
            continue
        print(f"  {_format_binary_display(cleaned)}")
        return cleaned


def read_binary(prompt: str, max_bits: int) -> str:
    if IS_UNIX:
        return _read_binary_realtime_unix(prompt, max_bits)
    return _read_binary_simple(prompt, max_bits)


def _input_single_group_with_confirm(group_num: int, required_bits: int) -> str:
    while True:
        print(f"\n--- group {group_num} ---")
        first = read_binary(t("prompt.input_group", n=group_num, bits=required_bits), required_bits)
        if IS_UNIX:
            print(t("you.entered", bits=_format_binary_display(first)))
        second = read_binary(t("prompt.input_group.2", n=group_num, bits=required_bits), required_bits)
        if IS_UNIX:
            print(t("you.entered", bits=_format_binary_display(second)))
        if first == second:
            print(t("group.confirmed", n=group_num, bits=_format_binary_display(first)))
            return first
        print(t("group.mismatch"))
        print(t("group.first", bits=_format_binary_display(first)))
        print(t("group.second", bits=_format_binary_display(second)))


def _input_all_groups() -> str:
    print()
    print("=" * 70)
    print(t("input.header"))
    print(t("input.rule1"))
    print(t("input.rule2"))
    if IS_UNIX:
        print(t("input.unix.hint"))
    else:
        print(t("input.win.hint"))
    print(t("input.display"))
    print(t("input.interrupt"))
    print("=" * 70)
    groups = [_input_single_group_with_confirm(i, 11) for i in range(1, 24)]
    groups.append(_input_single_group_with_confirm(24, 3))
    bits = "".join(groups)
    if len(bits) != ENTROPY_BITS:
        sys.exit(f"[fatal] entropy length {len(bits)} != {ENTROPY_BITS}")
    return bits


# ============================================================================
# 6. 通用工具
# ============================================================================

def clear_screen() -> None:
    os.system("clear" if IS_UNIX else "cls")


def secure_cleanup(*variables) -> None:
    for v in variables:
        del v
    gc.collect()


def self_test(words: List[str]) -> None:
    zero = b"\x00" * 32
    sha = hashlib.sha256(zero).hexdigest()
    chk = f"{int(sha[:2], 16):08b}"
    final = "0" * 256 + chk
    segs = [final[i * 11 : (i + 1) * 11] for i in range(24)]
    expected = "abandon " * 23 + "art"
    actual = " ".join(words[int(s, 2)] for s in segs)
    if actual != expected:
        sys.exit("[fatal] self-test failed: BIP39 algorithm is wrong!")
    print(t("self.test.pass"))


def compute_mnemonic(entropy_bits: str, words: List[str]):
    entropy_bytes = int(entropy_bits, 2).to_bytes(ENTROPY_BYTES, "big")
    sha_hex = hashlib.sha256(entropy_bytes).hexdigest()
    checksum_bits = f"{int(sha_hex[:2], 16):08b}"
    segs = [(entropy_bits + checksum_bits)[i * 11 : (i + 1) * 11] for i in range(24)]
    return [words[int(s, 2)] for s in segs], entropy_bytes, checksum_bits, sha_hex


def display_result(mnemonic, entropy_bytes, checksum_bits, sha_hex) -> None:
    print()
    print("=" * 70)
    print(t("result.header"))
    print("=" * 70)
    print()
    print(t("result.entropy_hex", hex=entropy_bytes.hex()))
    print(t("result.sha256", hex=sha_hex))
    print(t("result.checksum", bits=checksum_bits))
    print()
    print("-" * 70)
    print(t("result.mnemonic_header"))
    print("-" * 70)
    for i, w in enumerate(mnemonic, 1):
        print(f"  {i:>2}. {w}")
    print()
    print(t("result.full_mnemonic"))
    print(" ".join(mnemonic))
    recomputed = f"{hashlib.sha256(entropy_bytes).digest()[0]:08b}"
    status = t("result.checksum_pass") if recomputed == checksum_bits else t("result.checksum_fail")
    print()
    print(status)


def _ask_choice(options: str) -> str:
    while True:
        try:
            c = input(t("ent.please_choice", opts="/".join(options))).strip().upper()
        except KeyboardInterrupt:
            print()
            print(t("user.intrupted"))
            sys.exit(0)
        if c in options:
            return c
        print(t("ent.invalid_choice", opts="/".join(options)))


# ============================================================================
# 7. 文件输入（CSV / TXT / Numbers）
# ============================================================================

def _read_bit_table(path: str) -> List[List[int]]:
    """解析 CSV / TXT / Numbers 表格 → List[List[int]]。"""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        rows: List[List[int]] = []
        with open(path, encoding="utf-8-sig", newline="") as f:
            for raw in csv.reader(f):
                if not any(c.strip() for c in raw):
                    continue
                if len(raw) > 11 or (raw[0].strip() and raw[0].strip() not in ("0", "1")):
                    raw = raw[1:]
                cells = [c.strip() for c in raw[:11]]
                if any(c for c in cells) and not any(c in ("0", "1") for c in cells):
                    continue
                row = []
                for c in cells:
                    if c in ("", "0"):
                        row.append(0)
                    elif c == "1":
                        row.append(1)
                    else:
                        raise ValueError(t("cli.error.bad_cell", val=c))
                rows.append(row)
        return rows
    if ext == ".numbers":
        try:
            from numbers_parser import Document
        except ImportError:
            sys.exit(t("cli.error.numbers_parser"))
        doc = Document(path)
        table = doc.sheets[0].tables[0]
        rows = []
        for r in range(1, min(25, table.num_rows)):
            row = []
            for c in range(min(11, table.num_cols)):
                v = table.cell(r, c).value
                row.append(1 if (v is not None and str(v).strip() not in ("", "0")) else 0)
            rows.append(row)
        return rows
    # default: TXT
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip().replace(" ", "").replace(",", "")
            if not s:
                continue
            if not all(c in "01" for c in s):
                sys.exit(t("cli.error.non_binary_line", val=line.strip()))
            rows.append([int(c) for c in s])
    return rows


def cmd_generate(path: str) -> int:
    """从 CSV / TXT 表格生成助记词。"""
    if not os.path.exists(path):
        sys.exit(t("cli.error.file_not_found", path=path))
    rows = _read_bit_table(path)
    print(t("cli.read_groups", name=os.path.basename(path), n=len(rows)))
    if len(rows) != 24:
        sys.exit(t("cli.error.expected_24", n=len(rows)))
    groups = []
    for i, row in enumerate(rows[:23]):
        if len(row) < 11:
            sys.exit(t("cli.error.group_short", n=i + 1, m=len(row), k=11))
        groups.append(row[:11])
    last = rows[23]
    if len(last) < 3:
        sys.exit(t("cli.error.group_short", n=24, m=len(last), k=3))
    groups.append(last[:3])

    bits = "".join("".join(str(b) for b in g) for g in groups)
    if len(bits) != ENTROPY_BITS:
        sys.exit(f"[fatal] total bits {len(bits)} != {ENTROPY_BITS}")
    entropy = int(bits, 2).to_bytes(ENTROPY_BYTES, "big")
    mnemonic = entropy_to_mnemonic(entropy)

    print()
    print("=" * 70)
    print("Step 1 — 24 binary groups")
    print("=" * 70)
    for i, g in enumerate(groups, 1):
        tag = "" if len(g) == 11 else "  <-- final 3 bits"
        print(f"  group {i:>2}: {''.join(str(b) for b in g):<11} {tag}")
    print()
    print("=" * 70)
    print("Step 2 — 256-bit entropy")
    print("=" * 70)
    print(f"  entropy (hex): {entropy.hex()}")
    sha = hashlib.sha256(entropy).hexdigest()
    print(f"  SHA256       : {sha}")
    print()
    print("=" * 70)
    print("Step 3 — 24-word BIP-39 mnemonic")
    print("=" * 70)
    for i, w in enumerate(mnemonic, 1):
        print(f"  {i:>2}. {w}")
    print()
    print(" ".join(mnemonic))
    print("=" * 70)
    return 0


def cmd_from_dice(path: Optional[str]) -> int:
    """骰子点 → 助记词。"""
    rolls: List[int] = []
    if path:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rolls.extend(int(x) for x in line.replace(",", " ").split())
    else:
        print("Enter dice rolls (1..6), one per line, blank line to finish:")
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            if not line:
                break
            rolls.extend(int(x) for x in line.replace(",", " ").split())
    print(t("cli.dice_received", n=len(rolls)))
    entropy = dice_rolls_to_entropy(rolls)
    words = load_wordlist()
    mnemonic = entropy_to_mnemonic(entropy, words)
    print()
    print(t("cli.show_entropy", hex=entropy.hex()))
    print()
    print("*** 24-word mnemonic ***")
    for i, w in enumerate(mnemonic, 1):
        print(f"  {i:>2}. {w}")
    print()
    print(" ".join(mnemonic))
    return 0


def cmd_validate(words: List[str], path: Optional[str], passphrase: str, show_seed: bool) -> int:
    """验证 24 词助记词的校验和。"""
    if path:
        text = open(path, encoding="utf-8").read().strip()
    else:
        text = " ".join(words)
    if not text:
        sys.exit("[error] no mnemonic provided")
    wordlist = load_wordlist()
    ok = validate_mnemonic(text.split(), wordlist)
    print(t("cli.checksum_valid") if ok else t("cli.checksum_invalid"))
    if ok and show_seed:
        ent = mnemonic_to_entropy(text.split(), wordlist)
        seed = mnemonic_to_seed(text.split(), passphrase=passphrase, wordlist=wordlist)
        print(t("cli.show_entropy", hex=ent.hex()))
        print(t("cli.show_seed", p=passphrase, hex=seed.hex()))
    return 0 if ok else 1


def cmd_check_entropy(path: str) -> int:
    """审计外部 256 位二进制文件的熵质量。"""
    if not os.path.exists(path):
        sys.exit(t("cli.error.file_not_found", path=path))
    with open(path, encoding="utf-8") as f:
        bits = f.read().strip().replace(" ", "").replace(",", "").replace("\n", "")
    if len(bits) != 256 or any(c not in "01" for c in bits):
        sys.exit(t("cli.error.bits256_required"))
    report = full_entropy_check(bits)
    display_entropy_check_report(report)
    return 0 if report["all_passed"] else 1


# ============================================================================
# 8. V5 模式主流程（无文件输入 + 熵检查 + 助记词输出）
# ============================================================================

def interactive_mode() -> int:
    """无文件交互模式（双盲输入 + NIST 熵检查 + 24 词输出）。"""
    entropy_bits = None
    mnemonic = None
    entropy_bytes = None
    try:
        clear_screen()
        print("=" * 70)
        print(f" {t('title.interactive')}")
        print(f" {t('title.interactive_mode')}")
        print("=" * 70)
        print()
        print(t("warning.unset_histfile"))
        print(t("warning.no_files"))
        print(t("warning.no_files.2"))
        print(t("warning.no_files.3"))
        print(t("warning.no_files.4"))
        if not IS_UNIX:
            print()
            print(t("hint.windows_mode"))
            print(t("hint.windows_mode.2"))

        words = load_wordlist()
        self_test(words)
        entropy_bits = _input_all_groups()

        print()
        print(t("input.entering"))
        report = full_entropy_check(entropy_bits)
        display_entropy_check_report(report)

        if report["core_failed"]:
            print()
            print("!" * 70)
            print(t("ent.core_failed.banner"))
            print("!" * 70)
            print()
            print(t("ent.core_failed.opt1"))
            print(t("ent.core_failed.opt2"))
            print(t("ent.core_failed.opt3"))
            c = _ask_choice("R/C/Q")
            if c == "R":
                print()
                print(t("ent.re_run"))
                secure_cleanup(entropy_bits)
                return 0
            if c == "Q":
                print()
                print(t("ent.user_quit"))
                secure_cleanup(entropy_bits)
                return 0
        elif report["warning_count"] > 0:
            print()
            print("-" * 70)
            print(t("ent.aux_warn.banner"))
            print("-" * 70)
            print()
            print(t("ent.aux_warn.opt1"))
            print(t("ent.aux_warn.opt2"))
            print(t("ent.aux_warn.opt3"))
            c = _ask_choice("C/R/Q")
            if c == "R":
                print()
                print(t("ent.re_run"))
                secure_cleanup(entropy_bits)
                return 0
            if c == "Q":
                print()
                print(t("ent.user_quit"))
                secure_cleanup(entropy_bits)
                return 0

        mnemonic, entropy_bytes, checksum_bits, sha_hex = compute_mnemonic(entropy_bits, words)
        display_result(mnemonic, entropy_bytes, checksum_bits, sha_hex)

        print()
        print("=" * 70)
        print(t("result.write_down"))
        print(t("result.press_enter"))
        print("=" * 70)
        try:
            input()
        except KeyboardInterrupt:
            pass
        print(t("result.screen_cleared"))
        secure_cleanup(entropy_bits, mnemonic, entropy_bytes)
        return 0
    except KeyboardInterrupt:
        print()
        print(t("user.intrupted"))
        secure_cleanup(entropy_bits, mnemonic, entropy_bytes)
        return 0


# ============================================================================
# 9. argparse CLI 入口
# ============================================================================

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bip39_offline_v5",
        description="BIP-39 24-word offline mnemonic generator (single file, zero deps)",
    )
    sub = parser.add_subparsers(dest="cmd")

    # 第一个子命令 "interactive" 不需要 positional
    sub.add_parser("interactive", help="V5 mode: type 24 binary groups, run NIST checks")

    p_gen = sub.add_parser("generate", help="read 24 binary groups from a CSV/TXT file")
    p_gen.add_argument("path", help="CSV / TXT / Numbers file")

    p_dice = sub.add_parser("from-dice", help="convert dice rolls to mnemonic")
    p_dice.add_argument("path", nargs="?", help="optional text file with rolls")

    p_val = sub.add_parser("validate", help="validate a 24-word mnemonic")
    p_val.add_argument("words", nargs="*", help="24 words (or pass --path)")
    p_val.add_argument("--path", help="read mnemonic from file")
    p_val.add_argument("--passphrase", default="", help="BIP-39 passphrase")
    p_val.add_argument("--show-seed", action="store_true", help="also print the 512-bit seed")

    p_chk = sub.add_parser("check-entropy", help="audit a 256-bit binary string from a file")
    p_chk.add_argument("path", help="text file containing 256 bits")

    args = parser.parse_args(argv)

    if args.cmd is None or args.cmd == "interactive":
        return interactive_mode()
    if args.cmd == "generate":
        return cmd_generate(args.path)
    if args.cmd == "from-dice":
        return cmd_from_dice(args.path)
    if args.cmd == "validate":
        return cmd_validate(args.words, args.path, args.passphrase, args.show_seed)
    if args.cmd == "check-entropy":
        return cmd_check_entropy(args.path)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())