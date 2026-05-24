"""
ASGI 应用入口模块

本模块负责：
1. 设置 Django 运行环境变量
2. 初始化 Django ASGI 应用实例
3. 提供 ASGI lifespan 协议支持（startup/shutdown 生命周期）
4. 代理所有 HTTP/WebSocket 请求到 Django 应用

注意：使用 Granian 作为 ASGI 服务器时，必须实现 lifespan 协议
以避免启动时的 "ASGI Lifespan errored" 警告。
"""
import os

from django.core.asgi import get_asgi_application

# 设置 Django 配置模块路径，必须在调用 get_asgi_application 之前设置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'novel_reader.settings')

# 初始化 Django ASGI 应用实例（处理 HTTP/WebSocket 请求）
_django_app = get_asgi_application()


async def application(scope, receive, send):
    """
    ASGI 应用入口函数，处理所有 ASGI 协议类型。

    参数:
        scope: 字典，包含请求的元数据（type、method、path、headers 等）
        receive: 协程函数，用于从客户端接收消息
        send: 协程函数，用于向客户端发送响应

    行为:
        - 当 scope['type'] == 'lifespan' 时，处理 ASGI 生命周期事件
          * lifespan.startup -> 发送 startup.complete 完成响应
          * lifespan.shutdown -> 发送 shutdown.complete 并退出
        - 其他类型（http/websocket）代理给 Django ASGI 应用处理
    """
    if scope['type'] == 'lifespan':
        # 处理 ASGI lifespan 生命周期事件
        # 这是 ASGI 3.0 规范定义的服务器与应用通信机制
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                # 服务器启动完成，通知应用准备就绪
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                # 服务器关闭，通知应用清理资源
                await send({'type': 'lifespan.shutdown.complete'})
                return
    else:
        # 非 lifespan 事件（HTTP/WebSocket 请求），代理给 Django 处理
        await _django_app(scope, receive, send)
