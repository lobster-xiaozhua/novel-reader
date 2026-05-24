"""
ASGI 应用入口模块

该模块定义了小说阅读器项目的 ASGI（Asynchronous Server Gateway Interface）
应用入口。它负责初始化 Django ASGI 应用，并处理 ASGI 生命周期事件
（lifespan startup/shutdown），使应用能够与 ASGI 服务器（如 Uvicorn、Daphne）
正确协作。
"""

import os

from django.core.asgi import get_asgi_application

# 设置 Django 默认配置模块，确保 ASGI 服务器启动时加载正确的 settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'novel_reader.settings')

# 初始化 Django ASGI 应用，该调用会完成 Django 的所有启动流程
_django_app = get_asgi_application()


async def application(scope, receive, send):
    """
    ASGI 应用主入口函数。

    该函数是 ASGI 协议的标准入口点，接收 ASGI 连接的作用域（scope）、
    消息接收协程（receive）和消息发送协程（send）。

    对于 lifespan 类型的连接，负责处理服务器启动和关闭事件；
    对于其他类型（如 HTTP、WebSocket），则代理给 Django 原生 ASGI 应用处理。

    参数:
        scope (dict): ASGI 作用域字典，包含连接类型、路径、headers 等信息
        receive (callable): 异步协程，用于从客户端接收 ASGI 消息
        send (callable): 异步协程，用于向客户端发送 ASGI 消息

    返回:
        None: 该函数通过 send 发送响应，无显式返回值
    """
    if scope['type'] == 'lifespan':
        # lifespan 类型连接：处理服务器生命周期事件
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                # 服务器启动事件，通知 Django 已完成启动初始化
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                # 服务器关闭事件，通知 Django 已安全关闭
                await send({'type': 'lifespan.shutdown.complete'})
                return  # 退出循环，结束 lifespan 连接
    else:
        # 非 lifespan 连接（HTTP、WebSocket 等），交由 Django 原生 ASGI 应用处理
        await _django_app(scope, receive, send)
