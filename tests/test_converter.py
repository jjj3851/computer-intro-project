# -*- coding: utf-8 -*-
"""核心算法单元自测。

运行方式（仓库根目录）：
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.converter import (ConversionError, convert_with_steps, divide_with_steps,
                            expand_with_steps, format_in_base, parse_number)


class TestParse(unittest.TestCase):
    def test_decimal(self):
        self.assertEqual(parse_number("25", 10), 25)
        self.assertEqual(parse_number("  007 ", 10), 7)

    def test_hex_letters_case_insensitive(self):
        self.assertEqual(parse_number("ff", 16), 255)
        self.assertEqual(parse_number("0xFF", 16), 255)

    def test_prefixes(self):
        self.assertEqual(parse_number("0b101", 2), 5)
        self.assertEqual(parse_number("0o17", 8), 15)

    def test_invalid_char(self):
        with self.assertRaises(ConversionError):
            parse_number("102", 2)
        with self.assertRaises(ConversionError):
            parse_number("G", 16)
        with self.assertRaises(ConversionError):
            parse_number("8", 8)

    def test_empty_and_sign(self):
        for bad in ("", "   ", "-5", "+5"):
            with self.assertRaises(ConversionError):
                parse_number(bad, 10)


class TestDivide(unittest.TestCase):
    def test_25_to_bin(self):
        steps, digits = divide_with_steps(25, 2)
        self.assertEqual(digits, "11001")
        self.assertEqual(len(steps), 5)
        self.assertEqual(steps[0][:3], (25, 12, 1))     # 第一步：25 ÷ 2 = 12 余 1
        self.assertEqual(steps[-1][:3], (1, 0, 1))      # 最后一步：商为 0 停止
        self.assertTrue(all(len(s) == 4 and s[3] for s in steps))   # 第四元素为中文说明

    def test_zero_special_case(self):
        steps, digits = divide_with_steps(0, 2)
        self.assertEqual(digits, "0")
        self.assertEqual(len(steps), 1)

    def test_single_step(self):
        steps, digits = divide_with_steps(1, 2)
        self.assertEqual(digits, "1")
        self.assertEqual(len(steps), 1)

    def test_255_to_hex(self):
        _, digits = divide_with_steps(255, 16)
        self.assertEqual(digits, "FF")


class TestExpand(unittest.TestCase):
    def test_11001_from_bin(self):
        steps, value = expand_with_steps("11001", 2)
        self.assertEqual(value, 25)
        self.assertEqual(len(steps), 5)
        self.assertEqual(steps[0][:5], ("1", 0, 1, 1, 1))       # 个位最先
        self.assertEqual(steps[-1][:5], ("1", 4, 16, 16, 25))   # 最高位累计到 25

    def test_ff_from_hex(self):
        _, value = expand_with_steps("FF", 16)
        self.assertEqual(value, 255)


class TestConvert(unittest.TestCase):
    def test_dec_to_bin(self):
        r = convert_with_steps("25", 10, 2)
        self.assertEqual(r["mode"], "divide")
        self.assertEqual(r["result"], "11001")
        self.assertTrue(r["verify"])
        self.assertEqual(r["result_text"], "25(10) = 11001(2)")

    def test_bin_to_dec(self):
        r = convert_with_steps("11001", 2, 10)
        self.assertEqual(r["mode"], "expand")
        self.assertEqual(r["result"], "25")
        self.assertTrue(r["verify"])

    def test_hex_to_bin_two_stage(self):
        r = convert_with_steps("1F", 16, 2)
        self.assertEqual(r["mode"], "both")
        self.assertEqual(r["result"], "11111")
        self.assertTrue(r["verify"])
        self.assertEqual(len(r["expand_steps"]), 2)
        self.assertEqual(len(r["divide_steps"]), 5)

    def test_same_base(self):
        r = convert_with_steps("FF", 16, 16)
        self.assertEqual(r["mode"], "same")
        self.assertEqual(r["result"], "FF")
        self.assertTrue(r["verify"])

    def test_roundtrip_all_pairs(self):
        for v in (0, 1, 7, 8, 25, 63, 255, 1024, 65535, 4294967295):
            for b1 in (2, 8, 10, 16):
                s = format_in_base(v, b1)
                for b2 in (2, 8, 10, 16):
                    r = convert_with_steps(s, b1, b2)
                    self.assertTrue(r["verify"], f"{v}: {b1}->{b2} 校验失败")
                    self.assertEqual(parse_number(r["result"], b2), v)

    def test_big_number_hex(self):
        r = convert_with_steps("4294967295", 10, 16)
        self.assertEqual(r["result"], "FFFFFFFF")


if __name__ == "__main__":
    unittest.main(verbosity=2)
    def test_hex_with_letters_a5(self):
            # 十六进制 A5 转十进制：A(10)*16 + 5 = 165
            r = convert_with_steps("A5", 16, 10)
            self.assertEqual(r["result"], "165")
            self.assertTrue(r["verify"])
    
    def test_hex_with_letters_ff(self):
            # 十六进制 FF 转十进制：F(15)*16 + 15 = 255
            r = convert_with_steps("FF", 16, 10)
            self.assertEqual(r["result"], "255")
            self.assertTrue(r["verify"])
