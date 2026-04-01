from sqlalchemy.orm import Session

from app.models.role import Role


class RoleRepository:

    @staticmethod
    def get_by_name(db: Session, name: str) -> Role | None:
        return db.query(Role).filter(Role.nombre == name).first()

    @staticmethod
    def get_by_id(db: Session, role_id: int) -> Role | None:
        return db.query(Role).filter(Role.id_rol == role_id).first()

    @staticmethod
    def get_all(db: Session) -> list[Role]:
        return db.query(Role).order_by(Role.nombre.asc()).all()