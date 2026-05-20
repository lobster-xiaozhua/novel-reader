"""
测试覆盖缺口: apps.accounts.urls
风险分: 50
风险因素: 无测试文件
"""

import pytest
from django.test import RequestFactory, Client, TestCase
from apps.accounts.urls import *

