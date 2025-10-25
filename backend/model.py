from sqlalchemy import Column, Integer, String, Text
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    age = Column(Integer)
    current_study = Column(String)
    goal = Column(String)
    skills = Column(Text)
    document_path = Column(String)  # <--- Add this
    parsed_text = Column(Text)      # <--- Add this
