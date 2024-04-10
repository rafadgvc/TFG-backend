from sqlalchemy import select
from excepts import NoDataFound
from models.question.question import Question


def select_question(session, question_id):

    query = select(Question).where(Question.id == question_id)
    res = session.scalars(query).first()

    if res is None:
        raise NoDataFound

    return res


def insert_question(session, id):
    new_question = Question(id=id)
    session.add(new_question)
    session.commit()
