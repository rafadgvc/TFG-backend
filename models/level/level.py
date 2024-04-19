from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, delete, and_
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Set

from db.versions.db import Base
from models.level.level_schema import LevelSchema, LevelListSchema
from models.question.question_schema import QuestionSchema, QuestionListSchema, FullQuestionSchema
from models.subject.subject import Subject
from models.user.user import User
from utils.utils import get_current_user_id


class Level(Base):
    __tablename__ = "level"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subject.id"))
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("level.id"), nullable=True)

    # Relaciones
    created: Mapped["User"] = relationship(back_populates="levels")
    subject: Mapped["Subject"] = relationship(back_populates="levels")
    parent: Mapped["Level"] = relationship("Level", back_populates="children", remote_side=[id])
    children: Mapped[Set["Level"]] = relationship(
        "Level",
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    questions: Mapped[Set["Question"]] = relationship(
        back_populates="level",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
     return "<Level(id='%s', name='%s')>" % (self.id, self.name)

    @staticmethod
    def insert_level(
            session,
            name: str,
            subject_id: int,
            parent_id: int = None
    ) -> LevelSchema:
        user_id = get_current_user_id()
        query = select(Subject).where(
            and_(
            Subject.id == subject_id,
            Subject.created_by == user_id
            )
        )
        subject = session.execute(query).first()

        if not subject:
            abort(400, "La asignatura con el ID no ha sido encontrada.")

        if parent_id is not None:
            query = select(Level).where(
                and_(
                    Level.id == parent_id,
                    Level.created_by == user_id
                )
            )
            parent = session.execute(query).first()

            if not parent:
                abort(400, "El nivel superior con el ID no ha sido encontrado.")

        new_level = Level(name=name, subject_id=subject_id, created_by=user_id, parent_id=parent_id)
        session.add(new_level)
        session.commit()
        schema = LevelSchema().dump(new_level)
        return schema

    @staticmethod
    def get_level(
            session,
            id: int
    ) -> LevelSchema:
        query = select(Level).where(Level.id == id)
        res = session.execute(query).first()

        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")

        return res[0]

    @staticmethod
    def get_subject_levels(session, subject_id: int, limit: int = None, offset: int = 0) -> QuestionListSchema:
        current_user_id = get_current_user_id()
        query = select(Level).where(
            and_(
                Level.created_by == current_user_id,
                Level.subject_id == Level.subject_id
            )
        ).offset(offset)
        if limit:
            query = query.limit(limit)
        items = session.execute(query).scalars().all()

        total = session.query(Level).count()

        schema = LevelListSchema()
        return schema.dump({"items": items, "total": total})


