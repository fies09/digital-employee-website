#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/23 11:58
# @Author     : fany
# @Project    : PyCharm
# @File       : common.py
# @Description:
import secrets

def generate_secret_key() -> str:
    """生成安全的密钥"""
    return secrets.token_urlsafe(32)