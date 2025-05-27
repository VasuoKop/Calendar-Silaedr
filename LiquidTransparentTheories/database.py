
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from contextlib import contextmanager
from datetime import datetime

db_url = os.getenv('DATABASE_URL', 'sqlite:///database.db')
engine = create_engine(db_url)
Base = declarative_base()

note_classifications = Table('note_classifications', Base.metadata,
    Column('note_id', Integer, ForeignKey('notes.id')),
    Column('classification_id', Integer, ForeignKey('classifications.id'))
)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_admin = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

class Classification(Base):
    __tablename__ = 'classifications'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    notes = relationship('Note', secondary=note_classifications, back_populates='classifications')

class Note(Base):
    __tablename__ = 'notes'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    content = Column(String(500), nullable=False)
    classifications = relationship('Classification', secondary=note_classifications, back_populates='notes')

Session = sessionmaker(bind=engine)
SessionLocal = scoped_session(Session)

def init_db():
    Base.metadata.create_all(engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
