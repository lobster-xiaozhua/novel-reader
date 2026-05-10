from fastapi import APIRouter, Depends, HTTPException, Body, Query
from typing import Dict, List, Optional

from app.core.security import get_current_user
from app.services.version_service import version_manager

router = APIRouter(prefix="/version", tags=["版本管理"])


@router.post("/save")
async def save_version(
    name: str = Body(...),
    description: str = Body(""),
    tags: List[str] = Body(None),
    current_user = Depends(get_current_user),
):
    """
    保存当前项目状态为新版本

    示例:
    ```json
    {
        "name": "v1.0.0 初始版本",
        "description": "项目初始稳定版本",
        "tags": ["stable", "release"]
    }
    ```
    """
    try:
        snapshot = version_manager.create_version(
            name=name,
            description=description,
            tags=tags,
            auto_switch=True,
        )
        return {
            "success": True,
            "message": f"版本已保存: {snapshot.version_id}",
            "version": snapshot.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-save")
async def auto_save_version(
    current_user = Depends(get_current_user),
):
    """自动保存当前版本"""
    try:
        snapshot = version_manager.auto_save_version()
        return {
            "success": True,
            "message": f"自动保存完成: {snapshot.version_id}",
            "version": snapshot.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch/{version_id}")
async def switch_to_version(
    version_id: str,
    current_user = Depends(get_current_user),
):
    """切换到指定版本"""
    success = version_manager.switch_version(version_id)
    if not success:
        raise HTTPException(status_code=404, detail="版本不存在或切换失败")

    return {
        "success": True,
        "message": f"已切换到版本: {version_id}",
        "current_version": version_id,
    }


@router.get("/list")
async def list_versions(
    current_user = Depends(get_current_user),
):
    """列出所有版本"""
    versions = version_manager.list_versions()
    current = version_manager.get_current_version()
    return {
        "total": len(versions),
        "current_version": current.get("version_id") if current else None,
        "versions": versions,
    }


@router.get("/current")
async def get_current_version(
    current_user = Depends(get_current_user),
):
    """获取当前版本信息"""
    current = version_manager.get_current_version()
    if not current:
        return {
            "success": False,
            "message": "当前没有激活的版本",
        }
    return {
        "success": True,
        "version": current,
    }


@router.get("/detail/{version_id}")
async def get_version_detail(
    version_id: str,
    current_user = Depends(get_current_user),
):
    """获取版本详情"""
    detail = version_manager.get_version_detail(version_id)
    if not detail:
        raise HTTPException(status_code=404, detail="版本不存在")
    return {
        "success": True,
        "version": detail,
    }


@router.delete("/delete/{version_id}")
async def delete_version(
    version_id: str,
    current_user = Depends(get_current_user),
):
    """删除指定版本"""
    success = version_manager.delete_version(version_id)
    if not success:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {
        "success": True,
        "message": f"版本已删除: {version_id}",
    }


@router.post("/compare")
async def compare_versions(
    version_a: str = Body(...),
    version_b: str = Body(...),
    current_user = Depends(get_current_user),
):
    """
    比较两个版本的差异

    示例:
    ```json
    {
        "version_a": "v1_20240101_120000",
        "version_b": "v2_20240101_130000"
    }
    ```
    """
    try:
        result = version_manager.compare_versions(version_a, version_b)
        return {
            "success": True,
            "compare_result": result.to_dict(),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tag/{version_id}")
async def tag_version(
    version_id: str,
    tag: str = Body(..., embed=True),
    current_user = Depends(get_current_user),
):
    """为版本添加标签"""
    success = version_manager.tag_version(version_id, tag)
    if not success:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {
        "success": True,
        "message": f"标签 '{tag}' 已添加到版本 {version_id}",
    }


@router.post("/untag/{version_id}")
async def untag_version(
    version_id: str,
    tag: str = Body(..., embed=True),
    current_user = Depends(get_current_user),
):
    """移除版本标签"""
    success = version_manager.untag_version(version_id, tag)
    if not success:
        raise HTTPException(status_code=404, detail="版本不存在")

    return {
        "success": True,
        "message": f"标签 '{tag}' 已从版本 {version_id} 移除",
    }


@router.get("/find-by-tag")
async def find_versions_by_tag(
    tag: str = Query(..., description="标签名称"),
    current_user = Depends(get_current_user),
):
    """根据标签查找版本"""
    versions = version_manager.find_versions_by_tag(tag)
    return {
        "success": True,
        "tag": tag,
        "versions": versions,
    }
