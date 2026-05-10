from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, List, Optional

from app.core.security import get_current_user
from app.services.update_service import update_service, UpdateResult

router = APIRouter(prefix="/update", tags=["代码更新"])


@router.post("/execute")
async def execute_update(
    instruction: str = Body(..., embed=True),
    current_user = Depends(get_current_user),
):
    """
    执行代码更新指令

    支持的指令类型:
    - 添加模型 [ModelName] - 创建新的数据模型
    - 添加API [api_name] - 创建新的API路由
    - 添加路由 [route_name] - 添加新的路由模块
    - 修改配置 - 更新配置文件
    - 添加依赖 [package1, package2] - 添加Python依赖
    - 修复 [问题描述] - 扫描并修复代码问题

    示例:
    ```json
    {
        "instruction": "添加模型 Comment"
    }
    ```
    """
    result = update_service.execute_instruction(instruction)
    return result.to_dict()


@router.post("/plan")
async def preview_update_plan(
    instruction: str = Body(..., embed=True),
    current_user = Depends(get_current_user),
):
    """预览更新计划（不执行）"""
    plan = update_service.generate_update_plan(instruction)
    return {
        "instruction": plan["instruction"],
        "detected_structure": plan["detected_structure"],
        "actions_count": len(plan["actions"]),
        "actions": plan["actions"],
        "backup_files": plan["backup_files"],
    }


@router.get("/history")
async def get_update_history(
    current_user = Depends(get_current_user),
):
    """获取更新历史记录"""
    history = update_service.engine.get_update_history()
    return {
        "total": len(history),
        "updates": history,
    }


@router.post("/rollback")
async def rollback_last_update(
    current_user = Depends(get_current_user),
):
    """回滚最后一次更新"""
    result = update_service.engine.rollback_last_update()
    return result.to_dict()


@router.get("/structure")
async def detect_project_structure(
    current_user = Depends(get_current_user),
):
    """检测项目结构"""
    structure = update_service._detect_project_structure()
    return structure
