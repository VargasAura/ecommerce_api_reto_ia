import os

# Debe definirse antes de importar database/main: load_dotenv no sobrescribe
# variables ya presentes, y database.py exige DATABASE_URL al importar.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app
from models import Product, User

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr("main.time.sleep", lambda *_args, **_kwargs: None)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user(db):
    user = User(name="Ana Perez", email="ana@example.com")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def sample_products(db):
    cheap = Product(name="Cable USB", price=25.0, stock=10)
    expensive = Product(name="Monitor", price=150.0, stock=5)
    db.add_all([cheap, expensive])
    db.commit()
    db.refresh(cheap)
    db.refresh(expensive)
    return cheap, expensive
