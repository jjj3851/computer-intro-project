# -*- coding: utf-8 -*-
"""进位制转换核心算法。

本模块提供两类可逐帧回放的步骤记录，供界面“单步执行 / 自动播放”演示使用：

- 除基取余 divide_with_steps：十进制 → 任意进制，
  每一步记录 (被除数, 商, 余数, 中文说明)；
- 按权展开 expand_with_steps：任意进制 → 十进制，
  每一位记录 (数码, 幂次, 权值, 乘积, 累加和, 中文说明)。

convert_with_steps() 是对外统一入口，根据源/目标进制自动选择路径：
    目标进制为 10   → 按权展开 (expand)
    源进制为 10     → 除基取余 (divide)
    两者都不是 10   → 两阶段：先按权展开到十进制，再除基取余 (both)
    源 == 目标      → 直接返回结果 (same)
"""

DIGITS = "0123456789ABCDEF"          # 数码表：进制大于 10 时使用 A~F
SUPPORTED_BASES = (2, 8, 10, 16)     # 界面支持的进制
BASE_NAMES = {2: "二进制", 8: "八进制", 10: "十进制", 16: "十六进制"}
_PREFIXES = {2: ("0B",), 8: ("0O",), 16: ("0X",)}   # 允许的可选前缀


class ConversionError(ValueError):
    """输入校验错误（空输入、非法字符、负数等），UI 层捕获后提示用户。"""


def parse_number(text, base):
    """把指定进制的数字字符串校验并解析为非负整数。

    容忍：前后空白、下划线分隔、0B/0O/0X 前缀、小写 a-f；
    拒绝：空串、正负号、超出该进制数码表的任何字符。
    """
    if base not in SUPPORTED_BASES:
        raise ConversionError(f"不支持的进制：{base}（仅支持 2 / 8 / 10 / 16）")
    s = (text or "").strip().upper().replace("_", "").replace(" ", "")
    for p in _PREFIXES.get(base, ()):        # 去掉可选前缀
        if s.startswith(p):
            s = s[len(p):]
            break
    if not s:
        raise ConversionError("输入不能为空")
    if s[0] in "+-":
        raise ConversionError("仅支持非负整数，请勿输入正负号")
    for ch in s:
        idx = DIGITS.find(ch)
        if idx < 0 or idx >= base:
            raise ConversionError(f"字符 '{ch}' 在{BASE_NAMES[base]}（{base} 进制）中不合法")
    return int(s, base)


def format_in_base(value, base):
    """把非负整数写成 base 进制的数码串（内部工具函数）。"""
    if value == 0:
        return "0"
    out = []
    while value > 0:
        value, r = divmod(value, base)
        out.append(DIGITS[r])
    return "".join(reversed(out))


def divide_with_steps(n, base):
    """除基取余：把非负整数 n 转换为 base 进制。

    返回 (steps, digits)：
      steps  = [(被除数, 商, 余数, 中文说明), ...]，按计算顺序（先得最低位）；
      digits = 最终数码串（高位在前）。
    n == 0 特判：返回单步记录，避免界面无内容可演示。
    """
    if n == 0:
        return [(0, 0, 0, "输入为 0，转换结果直接为 0")], "0"
    raw = []                                   # 先收集 (被除数, 商, 余数) 原始三元组
    dividend = n
    while dividend > 0:
        quotient, remainder = divmod(dividend, base)
        raw.append((dividend, quotient, remainder))
        dividend = quotient
    last = len(raw) - 1
    steps = []
    for i, (a, q, r) in enumerate(raw):
        rem_ch = DIGITS[r]
        if last == 0:                          # n < base：一步除完
            note = f"商已为 0，余数 {rem_ch} 即为全部结果"
        elif i == 0:
            note = f"余数 {rem_ch} 为结果的最低位"
        elif i == last:
            note = f"商为 0，停止；余数 {rem_ch} 为结果的最高位"
        else:
            note = f"余数 {rem_ch} 为结果的下一位（自低向高）"
        steps.append((a, q, r, f"{a} ÷ {base} = {q} 余 {r}，{note}"))
    digits = "".join(DIGITS[r] for (_, _, r) in reversed(raw))   # 余数自下而上读取
    return steps, digits


def expand_with_steps(digits, base):
    """按权展开：把 base 进制数码串 digits（高位在前）展开为十进制。

    返回 (steps, value)：
      steps = [(数码, 幂次, 权值, 乘积, 累加和, 中文说明), ...]，从个位（幂 0）开始；
      value = 最终十进制数值。
    """
    rev = digits.upper()[::-1]                 # 从个位（最右，幂 0）开始累加
    steps, total = [], 0
    for power, ch in enumerate(rev):
        d = DIGITS.index(ch)
        weight = base ** power
        product = d * weight
        total += product
        if d == 0:
            note = "该位为 0，对总和无贡献"
        elif power == 0:
            note = "个位，权值为 1"
        else:
            note = f"权值 {base}^{power} = {weight}"
        steps.append((ch, power, weight, product, total,
                      f"数码 {ch}（值 {d}）× {base}^{power} = {product}，{note}，累加和 = {total}"))
    return steps, total


def convert_with_steps(text, from_base, to_base):
    """统一入口：解析输入 → 选择路径 → 返回界面回放所需的全部步骤与元信息。

    返回 dict 字段：
      mode          "same" / "divide" / "expand" / "both"
      input_text    规范化后的输入串
      value         解析出的十进制数值
      from_base / to_base   源、目标进制
      expand_steps  按权展开步骤列表（不含 expand 时为空表）
      divide_steps  除基取余步骤列表（不含 divide 时为空表）
      result        目标进制数码串
      result_text   形如 "25(10) = 11001(2)"
      verify        反向换算校验：result 按 to_base 解析回来是否等于 value
    """
    value = parse_number(text, from_base)
    if from_base == to_base:
        mode, expand_steps, divide_steps = "same", [], []
        result = format_in_base(value, to_base)
    elif to_base == 10:
        mode = "expand"
        expand_steps, dec = expand_with_steps(format_in_base(value, from_base), from_base)
        divide_steps, result = [], str(dec)
    elif from_base == 10:
        mode = "divide"
        expand_steps = []
        divide_steps, result = divide_with_steps(value, to_base)
    else:
        mode = "both"                          # 阶段1 展开到十进制 → 阶段2 除基取余
        expand_steps, dec = expand_with_steps(format_in_base(value, from_base), from_base)
        divide_steps, result = divide_with_steps(dec, to_base)
    verify = parse_number(result, to_base) == value     # 反向换算校验，确保结果正确
    return {
        "mode": mode,
        "input_text": (text or "").strip().upper(),
        "value": value,
        "from_base": from_base,
        "to_base": to_base,
        "expand_steps": expand_steps,
        "divide_steps": divide_steps,
        "result": result,
        "result_text": f"{value}({from_base}) = {result}({to_base})",
        "verify": verify,
    }
