import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine


load_dotenv(override=True)


def _default_sqlite_url() -> str:
    app_data_root = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA") or str(Path.home())
    db_dir = Path(app_data_root) / "NeuralAgent"
    db_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(db_dir / 'arkaios.db').as_posix()}"


DATABASE_URL = os.getenv("DATABASE_URL") or _default_sqlite_url()

engine = create_engine(
    DATABASE_URL, 
    echo=True, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(class_=Session, bind=engine, autocommit=False, autoflush=False)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
