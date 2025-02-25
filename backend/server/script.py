from datetime import datetime, timedelta
from . import session
from . import User


def delete_unconfirmed() -> None:
    now: datetime = datetime.now()
    three_days: datetime = now - timedelta(hours=72)
    users: list[User] = session.query(User).filter(User.confirmed == False, User.created_at < three_days).all()

    for user in users:
        session.delete(user)
    session.commit()
    
    print("Successfully deleted unconfirmed accounts")
    return
