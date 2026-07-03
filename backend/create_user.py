from sqlmodel import Session
from db.database import engine
from db.models import User, UserType
from utils.security import hash_password

def create_test_user():
    with Session(engine) as session:
        user = session.query(User).filter(User.email == "test@test.com").first()
        if not user:
            user = User(
                name="Test",
                email="test@test.com",
                password=hash_password("123456"),
                user_type=UserType.NORMAL_USER,
                is_email_verified=True
            )
            session.add(user)
            session.commit()
            print("Created test user")
        else:
            print("User already exists")

create_test_user()
