from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.analytics import (
    CategoriesAnalyticsResponse,
    MonthlyExpensesResponse,
    PurchaseHabitsResponse,
)
from app.services.analytics_service import AnalyticsService


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/monthly-expenses", response_model=MonthlyExpensesResponse)
def get_monthly_expenses(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AnalyticsService.get_monthly_expenses(
        db=db,
        current_user=current_user,
        year=year,
        month=month,
    )


@router.get("/categories", response_model=CategoriesAnalyticsResponse)
def get_categories_analytics(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AnalyticsService.get_categories_analytics(
        db=db,
        current_user=current_user,
        year=year,
        month=month,
    )


@router.get("/habits", response_model=PurchaseHabitsResponse)
def get_purchase_habits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AnalyticsService.get_purchase_habits(
        db=db,
        current_user=current_user,
    )
