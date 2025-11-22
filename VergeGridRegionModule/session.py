
# ================================================================
# VergeGrid Control Plane - Session Manager (Schema-Aware)
# ================================================================
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
import os

DB_USER = os.getenv('VG_DB_USER', 'vergegrid')
DB_PASS = os.getenv('VG_DB_PASS', 'vergegrid_password')
DB_HOST = os.getenv('VG_DB_HOST', 'localhost')
DB_NAME = os.getenv('VG_DB_NAME', 'vergegrid')
DB_PORT = os.getenv('VG_DB_PORT', '3306')

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20, pool_recycle=3600)

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from models import Base
    with engine.connect() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS vergegrid;"))  # Ensure schema exists
    Base.metadata.create_all(bind=engine)
    print("[VergeGrid] Database schema 'vergegrid' initialized successfully.")

if __name__ == "__main__":
    init_db()
