import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# LOAD ENV
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

print("DATABASE_URL LOADED:", DATABASE_URL)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ADD THIS BACK (CRITICAL)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()