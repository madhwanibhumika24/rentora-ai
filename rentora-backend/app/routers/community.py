from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.community_post import CommunityPost
from app.schemas.community import CommunityPostCreate, CommunityPostOut

router = APIRouter(prefix="/community", tags=["community"])


@router.post("/posts", response_model=CommunityPostOut)
def create_post(
    payload: CommunityPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    post = CommunityPost(
        property_id=payload.property_id,
        author_id=current_user.id,
        text=payload.text,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/posts", response_model=List[CommunityPostOut])
def list_posts(
    property_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(CommunityPost)
        .filter(CommunityPost.property_id == property_id)
        .order_by(CommunityPost.created_at.desc())
        .all()
    )