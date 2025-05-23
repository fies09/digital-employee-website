#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time       : 2025/5/21 14:52
# @Author     : fany
# @Project    : PyCharm
# @File       : merchant.py
# @Description:
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class MerchantRegister(BaseModel):
    merchant_name: str
    contact_person: str
    email: EmailStr
    phone: str
    business_license: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None

class MerchantResponse(BaseModel):
    id: str
    merchant_id: str
    merchant_name: str
    contact_person: str
    email: str
    phone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
