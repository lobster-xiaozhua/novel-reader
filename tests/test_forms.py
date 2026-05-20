"""
测试覆盖缺口: apps.accounts.forms
风险分: 80
风险因素: 无测试文件, 安全敏感: __init__
"""

import pytest
from django.test import RequestFactory, Client, TestCase
from apps.accounts.forms import *


class TestRegisterForm(TestCase):
    def test___init__(self):
        """测试 __init__ 基本行为"""
        pass
