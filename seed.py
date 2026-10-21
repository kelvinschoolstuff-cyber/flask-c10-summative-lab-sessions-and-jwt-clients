from faker import Faker

from app import create_app
from extensions import db
from models import Note, User


def seed_database():
    app = create_app()
    fake = Faker()
    with app.app_context():
        db.create_all()
        demo_user = User.query.filter_by(username="demo").first()
        if demo_user is None:
            demo_user = User(username="demo")
            demo_user.set_password("password123")
            db.session.add(demo_user)
            db.session.flush()
            for _ in range(10):
                db.session.add(
                    Note(
                        title=fake.sentence(nb_words=4).rstrip("."),
                        content=fake.paragraph(),
                        user_id=demo_user.id,
                    )
                )
            db.session.commit()
        print("Seed complete. Demo login: demo / password123")


if __name__ == "__main__":
    seed_database()