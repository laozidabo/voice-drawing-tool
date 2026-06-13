"""拼音模糊匹配模块

解决语音识别中常见的同音字/近音字问题。
例如：语音识别返回"画一个元"，实际想说"画一个圆"。
"""
from typing import Optional, List, Tuple
from pypinyin import pinyin, Style
import sys

# 绘图命令的拼音索引：(中文词, 拼音字符串)
# 使用模块级变量，通过 sys.modules 访问以确保获取最新值
_COMMAND_PINYIN_INDEX: List[Tuple[str, str]] = []


def _to_pinyin(text: str) -> str:
    """将中文转为拼音（不带声调，连续字符串）。"""
    return ''.join(p[0] for p in pinyin(text, style=Style.NORMAL))


def _edit_distance(s1: str, s2: str) -> int:
    """计算两个字符串的编辑距离。"""
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(min(
                curr_row[j] + 1,        # insert
                prev_row[j + 1] + 1,    # delete
                prev_row[j] + cost,      # replace
            ))
        prev_row = curr_row
    return prev_row[-1]


def build_pinyin_index(commands: List[str]):
    """为已知命令列表建立拼音索引。

    Args:
        commands: 中文命令词列表，如 ["圆", "圆形", "画圆", "红色", ...]
    """
    global _COMMAND_PINYIN_INDEX
    _COMMAND_PINYIN_INDEX = []
    seen = set()
    for cmd in commands:
        if cmd in seen:
            continue
        seen.add(cmd)
        py = _to_pinyin(cmd)
        if py:  # 跳过空拼音
            _COMMAND_PINYIN_INDEX.append((cmd, py))


def pinyin_fuzzy_match(text: str, max_distance: int = 1) -> Optional[str]:
    """拼音模糊匹配：将输入文本转为拼音，与已知命令的拼音比较。

    Args:
        text: 待匹配的中文文本
        max_distance: 最大允许编辑距离（默认 1）

    Returns:
        匹配到的中文命令词，或 None
    """
    # 通过模块访问全局变量，确保获取最新值
    module = sys.modules[__name__]
    pinyin_index = module._COMMAND_PINYIN_INDEX
    if not pinyin_index:
        return None

    input_py = _to_pinyin(text)
    if not input_py:
        return None

    best_match = None
    best_distance = max_distance + 1

    for cmd, cmd_py in pinyin_index:
        # 拼音完全匹配
        if input_py == cmd_py:
            return cmd
        # 编辑距离匹配
        dist = _edit_distance(input_py, cmd_py)
        if dist < best_distance:
            best_distance = dist
            best_match = cmd

    if best_distance <= max_distance:
        return best_match
    return None


def pinyin_replace_unknown(text: str, known_commands: List[str]) -> str:
    """尝试将文本中未知的中文词替换为拼音匹配的已知命令。

    策略：只匹配完整的已知命令词汇，不拆分复合词。
    例如："画一个元" → "画一个圆"（"元"匹配"圆"）
    但不会："画椭圆" → "画朵圆"（"椭圆"是完整词汇，不拆分）

    Args:
        text: 原始文本
        known_commands: 已知命令列表

    Returns:
        替换后的文本（尽可能修正同音字错误）
    """
    # 通过模块访问全局变量，确保获取最新值
    module = sys.modules[__name__]
    pinyin_index = module._COMMAND_PINYIN_INDEX
    if not pinyin_index:
        return text

    # 构建已知命令集合（用于跳过已知词汇）
    known_set = set(known_commands)

    result = text
    # 按长度从长到短尝试匹配（避免短词误匹配）
    for length in range(4, 1, -1):
        i = 0
        while i <= len(result) - length:
            substr = result[i:i + length]
            # 只对纯中文子串尝试匹配（跳过含数字/英文的子串）
            if not all('一' <= ch <= '鿿' for ch in substr):
                i += 1
                continue
            # 跳过已知命令（避免破坏"椭圆"等正确词汇）
            if substr in known_set:
                i += 1
                continue
            # 检查子串是否是任何已知命令的一部分或前缀（避免拆分复合词）
            is_part_of_known = False
            for known in known_set:
                if substr in known and substr != known:
                    is_part_of_known = True
                    break
                # 检查是否是已知命令的前缀
                if known.startswith(substr) and len(known) > len(substr):
                    is_part_of_known = True
                    break
            if is_part_of_known:
                i += 1
                continue
            match = pinyin_fuzzy_match(substr, max_distance=1)
            if match and match != substr:
                result = result[:i] + match + result[i + length:]
                i += len(match)
            else:
                i += 1

    return result
