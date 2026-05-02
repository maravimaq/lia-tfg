from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.user import User


class UserRepository:
    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id_usuario == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    @staticmethod
    def get_by_username(db: Session, username: str) -> User | None:
        return db.query(User).filter(User.nombre_usuario == username).first()

    @staticmethod
    def get_all(db: Session) -> list[User]:
        return db.query(User).all()

    @staticmethod
    def create(db: Session, user: User) -> User:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def save(db: Session, user: User) -> User:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete(db: Session, user: User) -> None:
        db.delete(user)
        db.commit()

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(func.count(User.id_usuario)).scalar() or 0

    @staticmethod
    def count_by_estado(db: Session, estado: str) -> int:
        return (
            db.query(func.count(User.id_usuario))
            .filter(User.estado == estado)
            .scalar()
            or 0
        )

    @staticmethod
    def get_latest_registered(db: Session) -> User | None:
        return (
            db.query(User)
            .options(joinedload(User.rol))
            .order_by(User.fecha_registro.desc())
            .first()
        )

    @staticmethod
    def get_paginated(
        db: Session,
        page: int,
        size: int,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        query = db.query(User).options(joinedload(User.rol))

        if search:
            like_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.nombre_usuario.ilike(like_term),
                    User.nombre_completo.ilike(like_term),
                    User.email.ilike(like_term),
                )
            )

        total = query.count()

        items = (
            query.order_by(User.fecha_registro.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

        return items, total

    @staticmethod
    def discover_users(
        db: Session,
        current_user_id: int,
        search: str | None = None,
    ) -> list[User]:
        query = db.query(User).filter(User.id_usuario != current_user_id)

        if search:
            like_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.nombre_usuario.ilike(like_term),
                    User.nombre_completo.ilike(like_term),
                    User.email.ilike(like_term),
                )
            )

        return query.order_by(User.nombre_completo.asc()).all()    