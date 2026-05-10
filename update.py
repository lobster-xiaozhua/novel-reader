#!/usr/bin/env python3
"""
Novel Reader 项目代码更新工具
支持通过自然语言指令更新项目代码，自适应修改

用法:
    python update.py "添加模型 Comment"
    python update.py "添加API review"
    python update.py "添加依赖 requests, numpy"
    python update.py "修改配置"
    python update.py --plan "添加模型 Comment"  # 仅预览
    python update.py --rollback  # 回滚最后一次更新
    python update.py --history   # 查看更新历史
    python update.py --structure # 查看项目结构
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.update_service import update_service


def print_header(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_success(msg: str):
    print(f"✅ {msg}")


def print_error(msg: str):
    print(f"❌ {msg}")


def print_info(msg: str):
    print(f"ℹ️  {msg}")


def print_warning(msg: str):
    print(f"⚠️  {msg}")


def execute_instruction(instruction: str):
    print_header(f"执行指令: {instruction}")

    result = update_service.execute_instruction(instruction)

    if result.success:
        print_success(result.message)
    else:
        print_error(result.message)

    if result.files_created:
        print_info("创建的文件:")
        for f in result.files_created:
            print(f"  + {f}")

    if result.files_modified:
        print_info("修改的文件:")
        for f in result.files_modified:
            print(f"  ~ {f}")

    if result.files_deleted:
        print_info("删除的文件:")
        for f in result.files_deleted:
            print(f"  - {f}")

    if result.backup_path:
        print_info(f"备份路径: {result.backup_path}")

    if result.errors:
        print_error("错误:")
        for e in result.errors:
            print(f"  ! {e}")

    return result.success


def preview_plan(instruction: str):
    print_header(f"预览更新计划: {instruction}")

    plan = update_service.generate_update_plan(instruction)

    print_info("检测到的项目结构:")
    for key, value in plan["detected_structure"].items():
        print(f"  {key}: {value}")

    print_info(f"计划执行 {len(plan['actions'])} 个操作:")
    for i, action in enumerate(plan["actions"], 1):
        action_type = action.get("type", "unknown")
        if action_type == "info":
            print(f"  {i}. ℹ️  {action.get('message', '')}")
        else:
            file_path = action.get("file", "N/A")
            print(f"  {i}. {action_type.upper()} -> {file_path}")

    if plan["backup_files"]:
        print_info("将备份的文件:")
        for f in plan["backup_files"]:
            print(f"  📦 {f}")

    return plan


def show_history():
    print_header("更新历史")

    history = update_service.engine.get_update_history()

    if not history:
        print_info("暂无更新记录")
        return

    print_info(f"共 {len(history)} 条更新记录:\n")

    for i, record in enumerate(history, 1):
        result = record.get("result", {})
        timestamp = record.get("timestamp", "未知时间")
        instruction = record.get("plan", {}).get("instruction", "未知指令")

        status = "✅ 成功" if result.get("success") else "❌ 失败"
        print(f"[{i}] {status} - {timestamp}")
        print(f"    指令: {instruction}")
        print(f"    创建: {len(result.get('files_created', []))} 修改: {len(result.get('files_modified', []))} 删除: {len(result.get('files_deleted', []))}")
        print()


def rollback():
    print_header("回滚最后一次更新")

    result = update_service.engine.rollback_last_update()

    if result.success:
        print_success(result.message)
    else:
        print_error(result.message)


def show_structure():
    print_header("项目结构检测")

    structure = update_service._detect_project_structure()

    for key, value in structure.items():
        icon = "✅" if value else "❌"
        if isinstance(value, str):
            print(f"{icon} {key}: {value}")
        else:
            print(f"{icon} {key}: {'是' if value else '否'}")


def main():
    parser = argparse.ArgumentParser(
        description="Novel Reader 项目代码更新工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python update.py "添加模型 Comment"
  python update.py "添加API review"
  python update.py "添加依赖 requests, numpy"
  python update.py --plan "添加模型 Comment"
  python update.py --rollback
  python update.py --history
  python update.py --structure
        """
    )

    parser.add_argument("instruction", nargs="?", help="更新指令")
    parser.add_argument("--plan", "-p", action="store_true", help="仅预览更新计划，不执行")
    parser.add_argument("--rollback", "-r", action="store_true", help="回滚最后一次更新")
    parser.add_argument("--history", "-H", action="store_true", help="查看更新历史")
    parser.add_argument("--structure", "-s", action="store_true", help="查看项目结构")
    parser.add_argument("--json", "-j", action="store_true", help="以JSON格式输出")

    args = parser.parse_args()

    if args.structure:
        show_structure()
        return

    if args.history:
        show_history()
        return

    if args.rollback:
        rollback()
        return

    if not args.instruction:
        parser.print_help()
        sys.exit(1)

    if args.plan:
        plan = preview_plan(args.instruction)
        if args.json:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        success = execute_instruction(args.instruction)
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
