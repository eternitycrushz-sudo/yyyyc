# -*- coding: utf-8 -*-
"""
数据清洗工具函数

处理常见的数据格式：
- 23w, 1.5万, 100亿 → 数字
- 23w-33w → (min, max)
- 12.5% → 0.125

原理讲解：
1. parse_number(): 解析带单位的数字
   - 支持 w/W/万/亿/k/K/m/M 等单位
   - 自动识别百分比
   
2. parse_range(): 解析范围值
   - 支持 "23w-33w" 格式
   - 返回 (min, max) 元组
   
3. clean_dict(): 根据配置批量清洗字典
   - 支持 number/range/percent/keep 四种类型
"""

import re
from typing import Tuple, Optional, Any, Dict


# 单位映射表
# w/W/万 = 10000
# 亿 = 100000000
# k/K = 1000
# m/M = 1000000
UNIT_MAP = {
    'w': 10000,
    'W': 10000,
    '万': 10000,
    '亿': 100000000,
    'k': 1000,
    'K': 1000,
    'm': 1000000,
    'M': 1000000,
}


def parse_number(value: Any) -> Optional[float]:
    """
    解析数字，支持带单位
    
    Examples:
        parse_number("23w") → 230000.0
        parse_number("1.5万") → 15000.0
        parse_number("100") → 100.0
        parse_number("12.5%") → 0.125
        parse_number(None) → None
        parse_number("15150") → 15150.0
    
    Args:
        value: 要解析的值（字符串、数字或 None）
        
    Returns:
        解析后的浮点数，无法解析返回 None
    """
    if value is None:
        return None
    
    # 已经是数字，直接返回
    if isinstance(value, (int, float)):
        return float(value)
    
    if not isinstance(value, str):
        return None
    
    value = value.strip()
    if not value or value == '-':
        return None
    
    # 处理百分比（如 "12.5%"）
    if value.endswith('%'):
        try:
            return float(value[:-1]) / 100
        except:
            return None
    
    # 提取数字和单位
    # 匹配格式：可选正负号 + 数字（可带小数） + 可选单位
    match = re.match(r'^([+-]?\d+\.?\d*)\s*([wW万亿kKmM]?)$', value)
    if match:
        num_str, unit = match.groups()
        try:
            num = float(num_str)
            multiplier = UNIT_MAP.get(unit, 1)
            return num * multiplier
        except:
            return None
    
    # 尝试直接转换（处理带逗号的数字如 "1,234"）
    try:
        return float(value.replace(',', ''))
    except:
        return None


def parse_range(value: Any) -> Tuple[Optional[float], Optional[float]]:
    """
    解析范围值，如 "23w-33w"
    
    Examples:
        parse_range("23w-33w") → (230000.0, 330000.0)
        parse_range("50w-75w") → (500000.0, 750000.0)
        parse_range("7.5w-10w") → (75000.0, 100000.0)
        parse_range("100") → (100.0, 100.0)
        parse_range(None) → (None, None)
    
    Args:
        value: 要解析的范围值
        
    Returns:
        (min_value, max_value) 元组
    """
    if value is None:
        return (None, None)
    
    # 已经是数字，返回相同的 min/max
    if isinstance(value, (int, float)):
        return (float(value), float(value))
    
    if not isinstance(value, str):
        return (None, None)
    
    value = value.strip()
    if not value or value == '-':
        return (None, None)
    
    # 尝试按 - 或 ~ 分割
    # 匹配格式：数字单位 - 数字单位
    match = re.match(
        r'^([+-]?\d+\.?\d*[wW万亿kKmM]?)\s*[-~]\s*([+-]?\d+\.?\d*[wW万亿kKmM]?)$',
        value
    )
    if match:
        min_str, max_str = match.groups()
        return (parse_number(min_str), parse_number(max_str))
    
    # 单个值，min = max
    num = parse_number(value)
    return (num, num)


def parse_percent(value: Any) -> Optional[float]:
    """
    解析百分比
    
    Examples:
        parse_percent("12.5%") → 0.125
        parse_percent("12.5") → 0.125 (假设是百分比值)
        parse_percent(0.125) → 0.125
        parse_percent(50) → 0.5 (大于1视为百分比)
    
    Args:
        value: 要解析的百分比值
        
    Returns:
        0-1 之间的小数
    """
    if value is None:
        return None
    
    if isinstance(value, (int, float)):
        # 如果大于1，假设是百分比值（如 50 表示 50%）
        if value > 1:
            return value / 100
        return float(value)
    
    if isinstance(value, str):
        value = value.strip()
        if value.endswith('%'):
            try:
                return float(value[:-1]) / 100
            except:
                return None
        try:
            num = float(value)
            if num > 1:
                return num / 100
            return num
        except:
            return None
    
    return None


def clean_dict(data: Dict, field_config: Dict[str, str]) -> Dict:
    """
    根据配置清洗字典数据
    
    Args:
        data: 原始数据字典
        field_config: 字段配置，格式：
            {
                'field_name': 'number',  # 转数字
                'field_name': 'range',   # 拆分范围（生成 _min/_max 两个字段）
                'field_name': 'percent', # 转百分比
                'field_name': 'keep',    # 保持原样
            }
    
    Returns:
        清洗后的字典
        
    Example:
        raw = {
            "follower_count": "15150",
            "range_last_price": "50w-75w",
            "nickname": "测试用户"
        }
        config = {
            "follower_count": "number",
            "range_last_price": "range",
            "nickname": "keep"
        }
        result = clean_dict(raw, config)
        # result = {
        #     "follower_count": 15150.0,
        #     "range_last_price_min": 500000.0,
        #     "range_last_price_max": 750000.0,
        #     "nickname": "测试用户"
        # }
    """
    result = {}
    
    for field, field_type in field_config.items():
        value = data.get(field)
        
        if field_type == 'number':
            result[field] = parse_number(value)
            
        elif field_type == 'range':
            # 范围字段拆分为 _min 和 _max
            min_val, max_val = parse_range(value)
            result[f'{field}_min'] = min_val
            result[f'{field}_max'] = max_val
            
        elif field_type == 'percent':
            result[field] = parse_percent(value)
            
        elif field_type == 'keep':
            result[field] = value
            
        else:
            # 未知类型，保持原样
            result[field] = value
    
    return result


if __name__ == '__main__':
    """测试清洗函数"""
    
    print("=== 测试 parse_number ===")
    test_cases = ["23w", "1.5万", "100", "12.5%", "15150", None, "-", "1,234"]
    for tc in test_cases:
        print(f"  {tc!r} → {parse_number(tc)}")
    
    print("\n=== 测试 parse_range ===")
    test_cases = ["50w-75w", "7.5w-10w", "23w-33w", "100", None, "1万~2万"]
    for tc in test_cases:
        print(f"  {tc!r} → {parse_range(tc)}")
    
    print("\n=== 测试 parse_percent ===")
    test_cases = ["12.5%", "50", 0.125, 50, None]
    for tc in test_cases:
        print(f"  {tc!r} → {parse_percent(tc)}")
    
    print("\n=== 测试 clean_dict ===")
    raw = {
        "follower_count": "15150",
        "range_last_price": "50w-75w",
        "range_last_sales": "7.5w-10w",
        "nickname": "测试用户",
        "commission_rate": "12.5%"
    }
    config = {
        "follower_count": "number",
        "range_last_price": "range",
        "range_last_sales": "range",
        "nickname": "keep",
        "commission_rate": "percent"
    }
    cleaned = clean_dict(raw, config)
    print(f"  原始: {raw}")
    print(f"  清洗后: {cleaned}")
