from fastapi import APIRouter, Request, Body, HTTPException
from models import Goal
from utils.helpers import serialize
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel
from typing import List

router = APIRouter()


class ManageGoalsRequest(BaseModel):
    """Request model for managing goals"""
    userId: str
    goals: List[str]


class GetGoalsRequest(BaseModel):
    """Request model for getting goals"""
    userId: str


@router.get("/")
async def get_all_goals(request: Request, userId: str = None):
    """Get all goals, optionally filtered by userId"""
    db = request.app.state.db
    query = {"userId": userId} if userId else {}
    return [serialize(g) async for g in db.goals.find(query)]


@router.post("/", response_model=Goal, status_code=201)
async def set_user_goals(request: Request, goal_data: Goal = Body(...)):
    """Set or update user goals (upsert operation)"""
    db = request.app.state.db

    await db.goals.update_one(
        {"userId": goal_data.userId},
        {"$set": {
            "goals": goal_data.goals,
            "updated_at": datetime.now()
        }},
        upsert=True
    )

    updated_goal = await db.goals.find_one({"userId": goal_data.userId})
    return serialize(updated_goal)


@router.get("/{user_id}", response_model=Goal)
async def get_user_goals(request: Request, user_id: str):
    """Get goals for a specific user by user_id"""
    db = request.app.state.db
    goal = await db.goals.find_one({"userId": user_id})
    if not goal:
        raise HTTPException(status_code=404, detail="Goals not found for this user")
    return serialize(goal)


@router.post("/manage-goals", status_code=200)
async def manage_goals(request: Request, goals_req: ManageGoalsRequest = Body(...)):
    """
    Create or update goals for a user.
    """
    db = request.app.state.db
    user_id = goals_req.userId
    goals = goals_req.goals

    print(f"📝 Managing goals for user: {user_id}")

    # Validate goals
    if not goals or len(goals) == 0:
        raise HTTPException(status_code=400, detail="Goals list cannot be empty")

    # Filter out empty goals
    filtered_goals = [goal.strip() for goal in goals if goal and goal.strip()]
    
    if len(filtered_goals) == 0:
        raise HTTPException(status_code=400, detail="Goals cannot be empty")

    # Upsert goals document
    result = await db.goals.update_one(
        {"userId": user_id},
        {
            "$set": {
                "goals": filtered_goals,
                "updated_at": datetime.now()
            },
            "$setOnInsert": {
                "created_at": datetime.now()
            }
        },
        upsert=True
    )

    # Fetch the updated/created goals
    goals_doc = await db.goals.find_one({"userId": user_id})
    
    print(f"✅ Goals {'updated' if result.modified_count > 0 else 'created'} successfully")
    
    return {
        "status": "success",
        "message": f"Goals {'updated' if result.modified_count > 0 else 'created'} successfully",
        "goals": serialize(goals_doc)
    }


@router.post("/get-goals", status_code=200)
async def get_goals(request: Request, goals_req: GetGoalsRequest = Body(...)):
    """
    Get goals for a specific user.
    """
    db = request.app.state.db
    user_id = goals_req.userId

    print(f"🔍 Fetching goals for user: {user_id}")

    # Find goals document
    goals_doc = await db.goals.find_one({"userId": user_id})
    
    if not goals_doc:
        # Return empty goals if not found
        return {
            "status": "success",
            "goals": {
                "userId": user_id,
                "goals": [],
                "isDefault": True
            }
        }
    
    print(f"✅ Goals found: {len(goals_doc.get('goals', []))} goals")
    
    return {
        "status": "success",
        "goals": serialize(goals_doc)
    }