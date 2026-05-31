#!/usr/bin/env python3
"""运行时日志查看工具 - 实时监控小说阅读器运行状态"""
import sys
import os
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / 'data' / 'logs'

LOG_FILES = {
    'app': 'app.log',
    'requests': 'requests.log',
    'auth': 'auth.log',
    'errors': 'errors.log',
    'crawler': 'crawler.log',
}

COLORS = {
    'DEBUG': '\033[36m',
    'INFO': '\033[32m',
    'WARNING': '\033[33m',
    'ERROR': '\033[31m',
    'CRITICAL': '\033[35m',
    'RESET': '\033[0m',
    'DIM': '\033[2m',
    'BOLD': '\033[1m',
    'TIME': '\033[90m',
}

def colorize_level(level):
    color = COLORS.get(level, COLORS['RESET'])
    return f'{color}{level}{COLORS["RESET"]}'

def tail_file(filepath, lines=50, follow=False):
    """实时跟踪日志文件"""
    if not filepath.exists():
        print(f'  ⚠️  日志文件不存在: {filepath.name}')
        return

    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        # 读取最后N行
        all_lines = f.readlines()
        for line in all_lines[-lines:]:
            print(_format_line(line.strip()))

        if not follow:
            return

        # 实时跟踪
        while True:
            line = f.readline()
            if line:
                print(_format_line(line.strip()), flush=True)
            else:
                time.sleep(0.1)

def _format_line(line):
    """高亮日志行"""
    for level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
        if f'] {level}]' in line or f'[{level}]' in line:
            parts = line.split(f'{level}]', 1)
            colored_level = colorize_level(level)
            return f'{parts[0]}{level}]{colored_level}{parts[1] if len(parts) > 1 else ""}'
    
    # 高亮分隔线
    if line.startswith('='):
        return f'{COLORS["DIM"]}{line}{COLORS["RESET"]}'
    
    return line

def show_stats():
    """显示日志统计信息"""
    print(f'\n{COLORS["BOLD"]}📊 日志统计{COLORS["RESET"]}')
    print(f'{"─" * 60}')
    
    total_lines = 0
    for name, filename in LOG_FILES.items():
        filepath = LOG_DIR / filename
        if filepath.exists():
            size_mb = filepath.stat().st_size / (1024 * 1024)
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
            total_lines += line_count
            print(f'  {name:12s}  {line_count:>8,} 行  |  {size_mb:>8.2f} MB')
        else:
            print(f'  {name:12s}  不存在')
    
    print(f'{"─" * 60}')
    print(f'  {"总计":12s}  {total_lines:>8,} 行')
    print()

def show_recent_errors(count=20):
    """显示最近的错误"""
    errors_file = LOG_DIR / 'errors.log'
    if not errors_file.exists():
        print('  ✅ 无错误日志')
        return
    
    print(f'\n{COLORS["BOLD"]}❌ 最近 {count} 条错误{COLORS["RESET"]}')
    print(f'{"─" * 60}')
    
    with open(errors_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    for line in lines[-count:]:
        line = line.strip()
        if line:
            print(_format_line(line))
    print()

def show_recent_requests(count=20):
    """显示最近的请求日志"""
    req_file = LOG_DIR / 'requests.log'
    if not req_file.exists():
        print('  ℹ️  无请求日志')
        return
    
    print(f'\n{COLORS["BOLD"]}🔄 最近 {count} 条请求{COLORS["RESET"]}')
    print(f'{"─" * 60}')
    
    with open(req_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    for line in lines[-count:]:
        line = line.strip()
        if line:
            print(_format_line(line))
    print()

def show_recent_auth(count=20):
    """显示最近的认证日志"""
    auth_file = LOG_DIR / 'auth.log'
    if not auth_file.exists():
        print('  ℹ️  无认证日志')
        return
    
    print(f'\n{COLORS["BOLD"]}🔐 最近 {count} 条认证{COLORS["RESET"]}')
    print(f'{"─" * 60}')
    
    with open(auth_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    for line in lines[-count:]:
        line = line.strip()
        if line:
            print(_format_line(line))
    print()

def main():
    if len(sys.argv) < 2:
        print(f'''{COLORS["BOLD"]}📖 Novel Reader 日志查看工具{COLORS["RESET"]}

用法:
  python logs_viewer.py <命令> [选项]

命令:
  stats           显示所有日志统计信息
  errors [N]      显示最近N条错误 (默认20)
  requests [N]    显示最近N条请求 (默认20)
  auth [N]        显示最近N条认证记录 (默认20)
  follow <type>   实时跟踪日志 (app/requests/auth/errors/crawler)
  tail <type> [N] 显示日志最后N行 (默认50)
  
示例:
  python logs_viewer.py stats
  python logs_viewer.py errors 50
  python logs_viewer.py follow requests
  python logs_viewer.py tail auth 100
''')
        return

    cmd = sys.argv[1].lower()
    
    if cmd == 'stats':
        show_stats()
    
    elif cmd == 'errors':
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        show_recent_errors(count)
    
    elif cmd == 'requests':
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        show_recent_requests(count)
    
    elif cmd == 'auth':
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        show_recent_auth(count)
    
    elif cmd == 'follow':
        if len(sys.argv) < 3:
            print('用法: python logs_viewer.py follow <app|requests|auth|errors|crawler>')
            return
        log_type = sys.argv[2]
        if log_type not in LOG_FILES:
            print(f'未知日志类型: {log_type}')
            print(f'可用类型: {", ".join(LOG_FILES.keys())}')
            return
        filepath = LOG_DIR / LOG_FILES[log_type]
        print(f'{COLORS["BOLD"]}📡 实时跟踪 {log_type} 日志...{COLORS["RESET"]}')
        print(f'{COLORS["DIM"]}Ctrl+C 退出{COLORS["RESET"]}')
        print(f'{"─" * 60}')
        try:
            tail_file(filepath, lines=0, follow=True)
        except KeyboardInterrupt:
            print(f'\n{COLORS["DIM"]}退出跟踪{COLORS["RESET"]}')
    
    elif cmd == 'tail':
        if len(sys.argv) < 3:
            print('用法: python logs_viewer.py tail <app|requests|auth|errors|crawler> [N]')
            return
        log_type = sys.argv[2]
        if log_type not in LOG_FILES:
            print(f'未知日志类型: {log_type}')
            print(f'可用类型: {", ".join(LOG_FILES.keys())}')
            return
        count = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        filepath = LOG_DIR / LOG_FILES[log_type]
        print(f'{COLORS["BOLD"]}📄 {log_type} 日志 (最后{count}行){COLORS["RESET"]}')
        print(f'{"─" * 60}')
        tail_file(filepath, lines=count, follow=False)
    
    else:
        print(f'未知命令: {cmd}')
        print('运行 python logs_viewer.py 查看帮助')

if __name__ == '__main__':
    main()
