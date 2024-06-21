from flask import abort
from sqlalchemy import Integer, String, select, ForeignKey, and_, delete, func, null, exists
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import Set

from db.versions.db import Base
from models.node.node_schema import NodeSchema, NodeListSchema
from models.question.question_schema import FullQuestionListSchema
from models.subject.subject import Subject
from models.user.user import User
from utils.utils import get_current_user_id
from models.associations.associations import node_question_association


class Node(Base):
    __tablename__ = "node"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, ForeignKey("subject.id"))
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("node.id"), nullable=True)

    # Relaciones
    created: Mapped["User"] = relationship(back_populates="nodes")
    subject: Mapped["Subject"] = relationship(back_populates="nodes")
    parent: Mapped["Node"] = relationship("Node", back_populates="children", remote_side=[id])
    children: Mapped[Set["Node"]] = relationship(
        "Node",
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True
    )
    questions = relationship(
        "Question",
        secondary=node_question_association,
        back_populates="nodes"
    )

    def __repr__(self):
     return "<Node(id='%s', name='%s')>" % (self.id, self.name)

    @hybrid_property
    def leaf(self):
        """
        Calculates if the nodes has no children.
        """
        return len(self.children) == 0

    @leaf.expression
    def leaf(cls):
        """
        Expresión SQLAlchemy to calculate if the nodes has no children.
        """
        return func.count(cls.children) == 0

    @hybrid_property
    def root(self):
        """
        Calculates if the node is a root node.
        """
        return self.parent_id is None

    @root.expression
    def root(cls):
        """
        Expresión SQLAlchemy to calculate if the node is a root node.
        """
        return cls.parent_id == null()

    @staticmethod
    def insert_node(
            session,
            name: str,
            subject_id: int,
            parent_id: int = None
    ) -> NodeSchema:
        user_id = get_current_user_id()
        query = select(Subject).where(
            and_(
            Subject.id == subject_id,
            Subject.created_by == user_id
            )
        )
        subject = session.execute(query).first()

        # The subject is checked to belong to the current user
        if not subject:
            abort(400, "La asignatura con el ID no ha sido encontrada.")

        # The node is checked to have an existing parent
        if parent_id is not None:
            query = select(Node).where(
                and_(
                    Node.id == parent_id,
                    Node.created_by == user_id
                )
            )
            parent = session.execute(query).first()

            if not parent:
                abort(400, "El nodo superior con el ID no ha sido encontrado.")
        
        # The node is added to the database
        new_node = Node(name=name, subject_id=subject_id, created_by=user_id, parent_id=parent_id)
        session.add(new_node)
        session.commit()
        schema = NodeSchema().dump(new_node)
        return schema

    @staticmethod
    def get_node(
            session,
            id: int
    ) -> NodeSchema:
        query = select(Node).where(Node.id == id)
        res = session.execute(query).first()

        # The node is checked to belong to the current user
        user_id = get_current_user_id()
        if res[0].created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")
        node = res[0]
        node_data = NodeSchema().dump(node)
        node_data['leaf'] = node.leaf
        return node_data

    @staticmethod
    def get_root_node(session, subject_id: int) -> NodeSchema:
        query = select(Node).where(
            and_(
                Node.subject_id == subject_id,
                Node.parent_id == null()
            )
        )
        
        root_node = session.execute(query).scalars().first()

        if not root_node:
            abort(404, "No se encontró un nodo raíz para la asignatura con el ID proporcionado.")

        # The node is checked to belong to the current user
        user_id = get_current_user_id()
        if root_node.created_by != user_id:
            abort(401, "No tienes acceso a este recurso.")
        
        return root_node

    @staticmethod
    def get_subject_nodes(session, subject_id: int, limit: int = None, offset: int = 0) -> NodeListSchema:
        
        # The nodes are checked to see if they belong to the current user
        current_user_id = get_current_user_id()
        query = select(Node).where(
            and_(
                Node.created_by == current_user_id,
                Node.subject_id == subject_id
            )
        ).offset(offset)
        if limit:
            query = query.limit(limit)
        items = session.execute(query).scalars().all()

        total = session.query(Node).count()

        schema = NodeListSchema()
        return schema.dump({"items": items, "total": total})

    @staticmethod
    def update_node(
            session,
            name: str,
            id: int
    ) -> NodeSchema:
        
        query = select(Node).where(Node.id == id)
        res = session.execute(query).first()

        # The node is checked to belong to the current user
        current_user_id = get_current_user_id()
        if res[0].created_by != current_user_id:
            abort(401, "No tienes acceso a este recurso.")

        # The node's name is changed
        res[0].name = name

        session.commit()

        schema = NodeSchema().dump(res[0])

        return schema

    @staticmethod
    def delete_node(
            session,
            id: int
    ) -> None:
        query = select(Node).where(Node.id == id)
        res = session.execute(query).first()

        # The node is checked to belong to the current user
        current_user_id = get_current_user_id()
        if res[0].created_by != current_user_id:
            abort(401, "No tienes acceso a este recurso.")

        # The node is deleted from the database
        query = delete(Node).where(Node.id == id)
        session.execute(query)
        session.commit()
