from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, List, Optional

from app.core.security import get_current_user, require_admin
from app.services.update_service import update_service, UpdateResult

router = APIRouter(prefix="/update", tags=["代码更新"])


@router.post("/execute")
async def execute_update(
    instruction: str = Body(..., embed=True),
    current_user=Depends(get_current_user),
):
    require_admin(current_user)
    result = update_service.execute_instruction(instruction)
    return result.to_dict()


@router.post("/plan")
async def preview_update_plan(
    instruction: str = Body(..., embed=True),
    current_user=Depends(get_current_user),
):
    require_admin(current_user)
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
    current_user=Depends(get_current_user),
):
    require_admin(current_user)
    history = update_service.engine.get_update_history()
    return {
        "total": len(history),
        "updates": history,
    }


@router.post("/rollback")
async def rollback_last_update(
    current_user=Depends(get_current_user),
):
    require_admin(current_user)
    result = update_service.engine.rollback_last_update()
    return result.to_dict()


@router.get("/structure")
async def detect_project_structure(
    current_user=Depends(get_current_user),
):
    require_admin(current_user)
    structure = update_service._detect_project_structure()
    return structure
