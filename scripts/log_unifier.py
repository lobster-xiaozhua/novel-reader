#!/usr/bin/env python3
"""
智能日志整合器 - 统一前后端日志输出
设计理念：
1. 统一时间线 - 所有日志按时间排序
2. 智能着色 - 不同服务用不同颜色
3. 智能过滤 - 自动过滤无用日志
4. 智能聚合 - 相同错误自动聚合
5. 实时分析 - 显示关键指标
"""

import sys
import time
import json
import re
import select
import os
from datetime import datetime
from collections import defaultdict, deque
from threading import Thread, Lock
import subprocess

# 颜色定义
COLORS = {
    'backend': '\033[36m',    # 青色
    'frontend': '\033[35m',   # 紫色
    'system': '\033[33m',     # 黄色
    'error': '\033[31m',      # 红色
    'warn': '\033[33m',       # 黄色
    'info': '\033[32m',       # 绿色
    'debug': '\033[37m',      # 白色
    'reset': '\033[0m',
    'bold': '\033[1m',
    'dim': '\033[2m',
}

# 日志级别优先级
LEVEL_PRIORITY = {'DEBUG': 0, 'INFO': 1, 'WARN': 2, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4, 'FATAL': 4}

# 需要过滤的噪声日志
NOISE_PATTERNS = [
    r'GET /(health|api/health).*200',
    r'favicon\.ico',
    r'GET /static/',
    r'GET /assets/',
    r'Hot Module Replacement',
    r'\[vite\]',
    r'page reload',
    r'hmr update',
]

class LogEntry:
    def __init__(self, source, raw_line, timestamp=None):
        self.source = source  # 'backend', 'frontend', 'system'
        self.raw = raw_line
        self.timestamp = timestamp or datetime.now()
        self.level = self._detect_level()
        self.message = self._extract_message()
        self.is_noise = self._check_noise()
        
    def _detect_level(self):
        line = self.raw.upper()
        if 'ERROR' in line or 'CRITICAL' in line or 'FATAL' in line:
            return 'ERROR'
        elif 'WARN' in line:
            return 'WARN'
        elif 'DEBUG' in line:
            return 'DEBUG'
        return 'INFO'
    
    def _extract_message(self):
        # 提取核心消息内容
        line = self.raw.strip()
        # 移除 ANSI 颜色码
        line = re.sub(r'\x1b\[[0-9;]*m', '', line)
        # 移除时间前缀
        line = re.sub(r'^\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}(\.\d+)?\s*', '', line)
        # 移除日志级别前缀
        line = re.sub(r'^(INFO|DEBUG|WARN|WARNING|ERROR|CRITICAL)\s*[:\-]?\s*', '', line, flags=re.I)
        return line[:120]  # 截断过长消息
    
    def _check_noise(self):
        for pattern in NOISE_PATTERNS:
            if re.search(pattern, self.raw, re.I):
                return True
        return False
    
    def format(self, show_source=True, show_time=True):
        parts = []
        
        if show_time:
            time_str = self.timestamp.strftime('%H:%M:%S')
            parts.append(f"{COLORS['dim']}{time_str}{COLORS['reset']}")
        
        if show_source:
            source_color = COLORS.get(self.source, '')
            source_icon = {'backend': '⚙', 'frontend': '◆', 'system': '●'}.get(self.source, '?')
            parts.append(f"{source_color}{source_icon} {self.source[:3].upper()}{COLORS['reset']}")
        
        level_color = COLORS.get(self.level.lower(), '')
        if self.level == 'ERROR':
            level_color = COLORS['error']
        elif self.level == 'WARN':
            level_color = COLORS['warn']
        
        level_icon = {'INFO': 'ℹ', 'DEBUG': '◊', 'WARN': '⚠', 'ERROR': '✖'}.get(self.level, '?')
        parts.append(f"{level_color}{level_icon}{COLORS['reset']}")
        
        message = self.message[:100]
        if self.level == 'ERROR':
            message = f"{COLORS['error']}{message}{COLORS['reset']}"
        elif self.level == 'WARN':
            message = f"{COLORS['warn']}{message}{COLORS['reset']}"
        
        parts.append(message)
        return ' '.join(parts)


class LogAggregator:
    def __init__(self, window_size=10):
        self.entries = deque(maxlen=1000)
        self.error_counts = defaultdict(int)
        self.last_errors = deque(maxlen=5)
        self.stats = {'backend': 0, 'frontend': 0, 'errors': 0, 'warnings': 0}
        self.lock = Lock()
        self.window_size = window_size
        
    def add(self, entry):
        with self.lock:
            self.entries.append(entry)
            self.stats[entry.source] += 1
            if entry.level == 'ERROR':
                self.stats['errors'] += 1
                self.error_counts[entry.message] += 1
                self.last_errors.append(entry)
            elif entry.level == 'WARN':
                self.stats['warnings'] += 1
    
    def get_recent_errors(self, n=3):
        with self.lock:
            return list(self.last_errors)[-n:]
    
    def get_top_errors(self, n=3):
        with self.lock:
            sorted_errors = sorted(self.error_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_errors[:n]
    
    def format_stats(self):
        with self.lock:
            return (
                f"{COLORS['dim']}Stats: "
                f"{COLORS['backend']}B:{self.stats['backend']}{COLORS['reset']} "
                f"{COLORS['frontend']}F:{self.stats['frontend']}{COLORS['reset']} "
                f"{COLORS['error']}E:{self.stats['errors']}{COLORS['reset']} "
                f"{COLORS['warn']}W:{self.stats['warnings']}{COLORS['reset']}"
            )


class SmartLogViewer:
    def __init__(self):
        self.aggregator = LogAggregator()
        self.running = True
        self.filter_noise = True
        self.show_stats = True
        self.last_stats_time = 0
        
    def process_line(self, source, line):
        entry = LogEntry(source, line)
        self.aggregator.add(entry)
        
        if self.filter_noise and entry.is_noise:
            return None
            
        return entry.format()
    
    def print_header(self):
        print(f"\n{COLORS['bold']}╔══════════════════════════════════════════════════════════════╗{COLORS['reset']}")
        print(f"{COLORS['bold']}║{COLORS['reset']}  {COLORS['cyan']}Novel Reader - 智能日志监控{COLORS['reset']}                              {COLORS['bold']}║{COLORS['reset']}")
        print(f"{COLORS['bold']}║{COLORS['reset']}  {COLORS['dim']}按 Ctrl+C 退出 | 按 n 切换噪声过滤 | 按 s 切换统计{COLORS['reset']}      {COLORS['bold']}║{COLORS['reset']}")
        print(f"{COLORS['bold']}╚══════════════════════════════════════════════════════════════╝{COLORS['reset']}\n")
    
    def print_stats_bar(self):
        if not self.show_stats:
            return
        stats = self.aggregator.format_stats()
        recent_errors = self.aggregator.get_recent_errors(2)
        
        print(f"\n{COLORS['dim']}─" * 60 + f"{COLORS['reset']}")
        print(f"  {stats}")
        
        if recent_errors:
            print(f"  {COLORS['error']}Recent Errors:{COLORS['reset']}")
            for err in recent_errors:
                print(f"    {COLORS['error']}✖ {err.message[:60]}{COLORS['reset']}")
        
        print(f"{COLORS['dim']}─" * 60 + f"{COLORS['reset']}\n")
    
    def watch_files(self, backend_log, frontend_log):
        self.print_header()
        
        # 使用 subprocess 实时读取
        backend_proc = subprocess.Popen(
            ['tail', '-f', backend_log],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        frontend_proc = subprocess.Popen(
            ['tail', '-f', frontend_log],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        def read_stream(proc, source):
            for line in iter(proc.stdout.readline, ''):
                if not self.running:
                    break
                formatted = self.process_line(source, line)
                if formatted:
                    print(formatted, flush=True)
                
                # 每 30 秒显示一次统计
                now = time.time()
                if now - self.last_stats_time > 30:
                    self.print_stats_bar()
                    self.last_stats_time = now
        
        backend_thread = Thread(target=read_stream, args=(backend_proc, 'backend'))
        frontend_thread = Thread(target=read_stream, args=(frontend_proc, 'frontend'))
        
        backend_thread.daemon = True
        frontend_thread.daemon = True
        
        backend_thread.start()
        frontend_thread.start()
        
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.running = False
            backend_proc.terminate()
            frontend_proc.terminate()
            print(f"\n{COLORS['dim']}日志监控已停止{COLORS['reset']}")


def main():
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'logs')
    backend_log = os.path.join(log_dir, 'backend.log')
    frontend_log = os.path.join(log_dir, 'frontend.log')
    
    if not os.path.exists(backend_log) and not os.path.exists(frontend_log):
        print(f"{COLORS['error']}错误: 日志文件不存在{COLORS['reset']}")
        print(f"请先启动项目: bash start.sh start")
        sys.exit(1)
    
    viewer = SmartLogViewer()
    viewer.watch_files(backend_log, frontend_log)


if __name__ == '__main__':
    main()
