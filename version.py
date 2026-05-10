#!/usr/bin/env python3
"""
Novel Reader 本地项目代码版本管理工具
支持版本保存、切换、对比、标签管理

用法:
    python version.py save "v1.0.0" -d "初始版本" -t stable
    python version.py auto-save
    python version.py list
    python version.py current
    python version.py switch v1_20240101_120000
    python version.py compare v1_xxx v2_xxx
    python version.py delete v1_xxx
    python version.py tag v1_xxx stable
    python version.py untag v1_xxx stable
    python version.py find-tag stable
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.version_service import version_manager


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


def cmd_save(args):
    print_header(f"保存版本: {args.name}")

    snapshot = version_manager.create_version(
        name=args.name,
        description=args.description or "",
        tags=args.tags or [],
        auto_switch=True,
    )

    print_success(f"版本已保存: {snapshot.version_id}")
    print_info(f"名称: {snapshot.name}")
    print_info(f"文件数: {len(snapshot.files)}")
    print_info(f"时间: {snapshot.timestamp}")
    if snapshot.tags:
        print_info(f"标签: {', '.join(snapshot.tags)}")


def cmd_auto_save(args):
    print_header("自动保存版本")

    snapshot = version_manager.auto_save_version()

    print_success(f"自动保存完成: {snapshot.version_id}")
    print_info(f"文件数: {len(snapshot.files)}")


def cmd_list(args):
    print_header("版本列表")

    versions = version_manager.list_versions()
    current = version_manager.get_current_version()

    if not versions:
        print_warning("暂无版本记录")
        return

    print_info(f"共 {len(versions)} 个版本:\n")

    for v in versions:
        marker = "👉 " if v["is_current"] else "   "
        status_icon = "🟢" if v["status"] == "active" else "⚪"
        print(f"{marker}{status_icon} {v['version_id']}")
        print(f"      名称: {v['name']}")
        print(f"      时间: {v['timestamp']}")
        print(f"      文件: {v['file_count']} 个")
        if v['tags']:
            print(f"      标签: {', '.join(v['tags'])}")
        print()


def cmd_current(args):
    print_header("当前版本")

    current = version_manager.get_current_version()
    if not current:
        print_warning("当前没有激活的版本")
        return

    print_info(f"版本ID: {current['version_id']}")
    print_info(f"名称: {current['name']}")
    print_info(f"描述: {current.get('description', '无')}")
    print_info(f"时间: {current['timestamp']}")
    print_info(f"文件数: {len(current['files'])}")
    if current.get('tags'):
        print_info(f"标签: {', '.join(current['tags'])}")


def cmd_switch(args):
    print_header(f"切换版本: {args.version_id}")

    success = version_manager.switch_version(args.version_id)
    if success:
        print_success(f"已切换到版本: {args.version_id}")
    else:
        print_error("版本不存在或切换失败")
        sys.exit(1)


def cmd_delete(args):
    print_header(f"删除版本: {args.version_id}")

    success = version_manager.delete_version(args.version_id)
    if success:
        print_success(f"版本已删除: {args.version_id}")
    else:
        print_error("版本不存在")
        sys.exit(1)


def cmd_compare(args):
    print_header(f"版本对比: {args.version_a} vs {args.version_b}")

    try:
        result = version_manager.compare_versions(args.version_a, args.version_b)
    except ValueError as e:
        print_error(str(e))
        sys.exit(1)

    print_info(f"新增文件: {len(result.files_added)}")
    print_info(f"删除文件: {len(result.files_deleted)}")
    print_info(f"修改文件: {len(result.files_modified)}")
    print_info(f"未变文件: {len(result.files_unchanged)}")

    if result.files_added:
        print("\n📁 新增文件:")
        for f in result.files_added:
            print(f"  + {f}")

    if result.files_deleted:
        print("\n🗑️  删除文件:")
        for f in result.files_deleted:
            print(f"  - {f}")

    if result.files_modified:
        print("\n✏️  修改文件:")
        for f in result.files_modified:
            print(f"  ~ {f}")

    if args.show_diff:
        print("\n" + "=" * 60)
        print("详细差异:")
        print("=" * 60)
        for diff in result.diffs:
            if diff.change_type in ("added", "deleted", "modified"):
                print(f"\n📄 {diff.file_path} ({diff.change_type})")
                if diff.diff_lines:
                    for line in diff.diff_lines[:50]:  # 限制显示行数
                        prefix = ""
                        if line.startswith("+"):
                            prefix = "\033[32m"  # 绿色
                        elif line.startswith("-"):
                            prefix = "\033[31m"  # 红色
                        elif line.startswith("@"):
                            prefix = "\033[36m"  # 青色
                        print(f"  {prefix}{line}\033[0m")
                    if len(diff.diff_lines) > 50:
                        print(f"  ... 还有 {len(diff.diff_lines) - 50} 行 ...")


def cmd_tag(args):
    print_header(f"添加标签: {args.tag} -> {args.version_id}")

    success = version_manager.tag_version(args.version_id, args.tag)
    if success:
        print_success(f"标签 '{args.tag}' 已添加")
    else:
        print_error("版本不存在")
        sys.exit(1)


def cmd_untag(args):
    print_header(f"移除标签: {args.tag} -> {args.version_id}")

    success = version_manager.untag_version(args.version_id, args.tag)
    if success:
        print_success(f"标签 '{args.tag}' 已移除")
    else:
        print_error("版本不存在")
        sys.exit(1)


def cmd_find_tag(args):
    print_header(f"查找标签: {args.tag}")

    versions = version_manager.find_versions_by_tag(args.tag)
    if not versions:
        print_warning(f"没有找到带有标签 '{args.tag}' 的版本")
        return

    print_info(f"找到 {len(versions)} 个版本:\n")
    for v in versions:
        marker = "👉 " if v["is_current"] else "   "
        print(f"{marker}{v['version_id']} - {v['name']}")
        print(f"      时间: {v['timestamp']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Novel Reader 本地项目代码版本管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python version.py save "v1.0.0" -d "初始版本" -t stable
  python version.py auto-save
  python version.py list
  python version.py switch v1_20240101_120000
  python version.py compare v1_xxx v2_xxx --show-diff
  python version.py tag v1_xxx stable
  python version.py find-tag stable
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # save
    save_parser = subparsers.add_parser("save", help="保存当前版本")
    save_parser.add_argument("name", help="版本名称")
    save_parser.add_argument("-d", "--description", help="版本描述")
    save_parser.add_argument("-t", "--tags", nargs="+", help="版本标签")

    # auto-save
    subparsers.add_parser("auto-save", help="自动保存版本")

    # list
    subparsers.add_parser("list", help="列出所有版本")

    # current
    subparsers.add_parser("current", help="显示当前版本")

    # switch
    switch_parser = subparsers.add_parser("switch", help="切换到指定版本")
    switch_parser.add_argument("version_id", help="版本ID")

    # delete
    delete_parser = subparsers.add_parser("delete", help="删除版本")
    delete_parser.add_argument("version_id", help="版本ID")

    # compare
    compare_parser = subparsers.add_parser("compare", help="比较两个版本")
    compare_parser.add_argument("version_a", help="版本A ID")
    compare_parser.add_argument("version_b", help="版本B ID")
    compare_parser.add_argument("--show-diff", action="store_true", help="显示详细差异")

    # tag
    tag_parser = subparsers.add_parser("tag", help="为版本添加标签")
    tag_parser.add_argument("version_id", help="版本ID")
    tag_parser.add_argument("tag", help="标签名称")

    # untag
    untag_parser = subparsers.add_parser("untag", help="移除版本标签")
    untag_parser.add_argument("version_id", help="版本ID")
    untag_parser.add_argument("tag", help="标签名称")

    # find-tag
    find_tag_parser = subparsers.add_parser("find-tag", help="根据标签查找版本")
    find_tag_parser.add_argument("tag", help="标签名称")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    command_map = {
        "save": cmd_save,
        "auto-save": cmd_auto_save,
        "list": cmd_list,
        "current": cmd_current,
        "switch": cmd_switch,
        "delete": cmd_delete,
        "compare": cmd_compare,
        "tag": cmd_tag,
        "untag": cmd_untag,
        "find-tag": cmd_find_tag,
    }

    handler = command_map.get(args.command)
    if handler:
        handler(args)
    else:
        print_error(f"未知命令: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
