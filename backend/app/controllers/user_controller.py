from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, security
from app.db.session import get_db
from app.models.user import User
from app.schemas.account_request import (
    AccountActionRequestCreate,
    AccountActionRequestResponse,
)
from app.schemas.bot_config import BotConfigResponse, BotConfigUpdate
from app.schemas.follow import (
    DiscoverUserResponse,
    FollowRequestAction,
    FollowRequestIncomingItem,
    FollowRequestResponse,
)
from app.schemas.preferences import PreferenciasResponse, PreferenciasUpdate
from app.schemas.session import SessionResponse
from app.schemas.user import ChangePasswordRequest, UserResponse, UserUpdate
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from fastapi.security import HTTPAuthorizationCredentials


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserService.get_profile(current_user)


@router.put("/me", response_model=UserResponse)
def update_me(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.update_profile(db, current_user, user_data)


@router.put("/me/password")
def change_password(
    request_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.change_password(db, current_user, request_data)


@router.get("/me/preferences", response_model=PreferenciasResponse)
def get_my_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.get_preferences(db, current_user)


@router.put("/me/preferences", response_model=PreferenciasResponse)
def update_my_preferences(
    preferences_data: PreferenciasUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.update_preferences(db, current_user, preferences_data)


@router.get("/me/sessions", response_model=list[SessionResponse])
def get_my_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.get_active_sessions(db, current_user)


@router.delete("/me/sessions/current")
def close_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return AuthService.logout(db, credentials.credentials)


@router.post(
    "/me/account-action-request",
    response_model=AccountActionRequestResponse,
)
def request_account_action(
    request_data: AccountActionRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.request_account_action(db, current_user, request_data)


@router.get("/discover", response_model=list[DiscoverUserResponse])
def discover_users(
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.discover_users(db, current_user, search)


@router.post("/follow-requests/{target_user_id}", response_model=FollowRequestResponse)
def request_follow(
    target_user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.request_follow(db, current_user, target_user_id)


@router.get(
    "/me/follow-requests/incoming",
    response_model=list[FollowRequestIncomingItem],
)
def get_incoming_follow_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.get_incoming_follow_requests(db, current_user)


@router.put("/me/follow-requests/{request_id}/respond")
def respond_follow_request(
    request_id: int,
    action: FollowRequestAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.respond_follow_request(db, current_user, request_id, action)


@router.get("/{user_id}/public", response_model=UserResponse)
def get_public_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return UserService.get_public_profile(db, user_id)