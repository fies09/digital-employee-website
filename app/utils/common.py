#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/23 11:58
# @Author     : fany
# @Project    : PyCharm
# @File       : common.py
# @Description:
import secrets
import string
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

def generate_secret_key(length: int = 32) -> str:
    """
    生成安全的密钥字符串

    Args:
        length: 密钥长度

    Returns:
        str: 生成的密钥
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_secure_token(length: int = 32) -> str:
    """
    生成安全令牌

    Args:
        length: 令牌长度

    Returns:
        str: 安全令牌
    """
    return secrets.token_urlsafe(length)


def hash_string(text: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    对字符串进行哈希加密

    Args:
        text: 要加密的文本
        salt: 盐值（可选）

    Returns:
        tuple: (哈希值, 盐值)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    # 使用PBKDF2进行哈希
    hashed = hashlib.pbkdf2_hmac(
        'sha256',
        text.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # 迭代次数
    )

    return hashed.hex(), salt


def verify_hash(text: str, hashed_text: str, salt: str) -> bool:
    """
    验证哈希

    Args:
        text: 原始文本
        hashed_text: 哈希值
        salt: 盐值

    Returns:
        bool: 是否匹配
    """
    new_hash, _ = hash_string(text, salt)
    return new_hash == hashed_text


def generate_uuid() -> str:
    """生成UUID"""
    return str(uuid.uuid4())


def generate_timestamp() -> str:
    """生成时间戳字符串"""
    return datetime.now().isoformat()


def safe_get_dict_value(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """安全获取字典值"""
    try:
        return data.get(key, default)
    except (AttributeError, TypeError):
        return default


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断字符串"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def validate_email(email: str) -> bool:
    """简单的邮箱验证"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """简单的手机号验证"""
    import re
    # 简单的中国手机号验证
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone.replace('-', '').replace(' ', '')))


def clean_string(text: str) -> str:
    """清理字符串（去除空白字符）"""
    return text.strip() if text else ""


def is_valid_url(url: str) -> bool:
    """验证URL格式"""
    import re
    pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?$'
    return bool(re.match(pattern, url))
