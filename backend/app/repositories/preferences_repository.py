from sqlalchemy.orm import Session

from app.models.preferencias_usuario import PreferenciasUsuario


class PreferencesRepository:
    @staticmethod
    def get_by_user_id(db: Session, user_id: int) -> PreferenciasUsuario | None:
        return (
            db.query(PreferenciasUsuario)
            .filter(PreferenciasUsuario.usuario_id == user_id)
            .first()
        )

    @staticmethod
    def create(db: Session, prefs: PreferenciasUsuario) -> PreferenciasUsuario:
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
        return prefs

    @staticmethod
    def save(db: Session, prefs: PreferenciasUsuario) -> PreferenciasUsuario:
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
        return prefs

    @staticmethod
    def get_or_create_by_user_id(db: Session, user_id: int) -> PreferenciasUsuario:
        prefs = PreferencesRepository.get_by_user_id(db, user_id)
        if prefs is not None:
            return prefs

        prefs = PreferenciasUsuario(usuario_id=user_id)
        return PreferencesRepository.create(db, prefs)
