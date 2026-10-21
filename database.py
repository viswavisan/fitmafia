import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

Base = declarative_base()


class DynamicSessionProxy:
    """Dynamically routes database queries between real DB and demo sandbox DB based on session state."""

    def __init__(self, real_session, demo_session_getter):
        self._real_session = real_session
        self._demo_session_getter = demo_session_getter

    def _get_current_session(self):
        try:
            from flask import has_request_context, session
            if has_request_context() and session.get('is_demo'):
                return self._demo_session_getter()
        except Exception:
            pass
        return self._real_session

    def __getattr__(self, name):
        return getattr(self._get_current_session(), name)

    def __call__(self, *args, **kwargs):
        return self._get_current_session()(*args, **kwargs)

    def __repr__(self):
        return repr(self._get_current_session())


def _make_engine(path_or_url, fallback_filename):
    raw = str(path_or_url or "").strip()
    if not raw or raw == "None":
        raw = f"/home/opc/{fallback_filename}"

    if raw.startswith("sqlite:///"):
        raw = raw[len("sqlite:///"):]
    elif raw.startswith("sqlite://"):
        raw = raw[len("sqlite://"):]

    parent = os.path.dirname(raw)
    if parent:
        try:
            os.makedirs(parent, exist_ok=True)
            test_file = os.path.join(parent, ".perm_check")
            with open(test_file, "a") as f:
                pass
            os.remove(test_file)
        except Exception:
            raw = os.path.basename(raw)

    return create_engine(f"sqlite:///{raw}", connect_args={"check_same_thread": False})


class Database:
    def __init__(self, db_url=None, demo_db_url=None):
        db_url = db_url or os.getenv("DATABASE_URL")
        demo_db_url = demo_db_url or os.getenv("DEMO_DATABASE_URL")
        self.engine = _make_engine(db_url, "fitmafia.db")
        self.demo_engine = _make_engine(demo_db_url, "fitmafia_demo.db")

        self._real_session = scoped_session(sessionmaker(bind=self.engine))
        self._demo_session = scoped_session(sessionmaker(bind=self.demo_engine))

        # Dynamic session proxy routes requests with session['is_demo'] to demo sandbox
        self.session = DynamicSessionProxy(self._real_session, lambda: self._demo_session)

    def init_db(self):
        """Creates all tables from model definitions if not already present."""
        Base.metadata.create_all(self.engine)
        Base.metadata.create_all(self.demo_engine)

    def reset_demo_db(self, force=False):
        """Resets the demo sandbox database using the standalone demo_data module."""
        from demo_data import reset_demo_db
        return reset_demo_db(db=self, force=force)