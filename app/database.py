import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# SQLite by default. For MySQL set, for example:
#   DATABASE_URL=mysql+pymysql://user:password@localhost:3306/shop
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shop.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
