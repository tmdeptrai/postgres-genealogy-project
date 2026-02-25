import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

load_dotenv()

class Base(DeclarativeBase):
    pass

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    poolclass=NullPool,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

print("Session established")