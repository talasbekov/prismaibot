import os
import sys

# Ensure backend/app is in PYTHONPATH
sys.path.append(os.path.join(os.getcwd(), "backend"))

from sqlmodel import Session, create_engine, text
from app.core.config import settings

# In tests/conftest.py, we saw settings are used to create the engine.
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

def reset_crisis_sessions():
    sql = text("""
        UPDATE telegram_session
        SET crisis_state = 'normal'
        WHERE crisis_state IN ('crisis_active', 'step_down_pending');
    """)
    with Session(engine) as session:
        result = session.execute(sql)
        session.commit()
        print(f"Successfully updated {result.rowcount} sessions.")

if __name__ == "__main__":
    try:
        reset_crisis_sessions()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
