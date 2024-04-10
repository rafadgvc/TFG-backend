from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker




url_object = URL.create(
    "postgresql",
    username="root",
    password="1a2b3c4d5e!$",  # plain (unescaped) text
    host="localhost",
    database="postgres",
    port="5432"
)


Base = declarative_base()

def create_db():
    engine = create_engine(url_object)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

