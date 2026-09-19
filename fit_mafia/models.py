import config
from sqlalchemy import Column, String, case
from sqlalchemy.orm import class_mapper
import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from database import Base, Database
import os

db = Database(os.getenv("DATABASE_URL"))
db_url = os.getenv("DATABASE_URL", "")
SCHEMA_NAME = 'fitmafia' if "postgres" in db_url else None

class Session(Base):
    __tablename__ = 'user_session'
    __table_args__ = {'schema': SCHEMA_NAME} if SCHEMA_NAME else {}
    session_id = Column(String(50), primary_key=True)
    start_time = Column(String(50), nullable=True)
    end_time = Column(String(50), nullable=True)
    user_name = Column(String(50), nullable=True)

class Member(Base):
    __tablename__ = 'member'
    __table_args__ = {'schema': SCHEMA_NAME} if SCHEMA_NAME else {}
    mobile_number = Column(String(10), primary_key=True)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    dob = Column(String(50), nullable=True)
    gender = Column(String(50), nullable=True)
    email = Column(String(50), nullable=True)
    address = Column(String(100), nullable=True)
    height = Column(String(10), nullable=True)
    weight = Column(String(10), nullable=True)
    bmi = Column(String(10), nullable=True)
    subscription = Column(String(50), nullable=True)
    joining_date = Column(String(50), nullable=True)
    subscription_start_date = Column(String(50), nullable=True)
    subscription_end_date = Column(String(50), nullable=True)
    photo = Column(String(225), nullable=True)
    password = Column(String(50), nullable=True)

    @hybrid_property
    def status(self):
        """Calculates status in Python code."""
        if not self.subscription_end_date:
            return 'expired'
        
        try:
            end_date = datetime.date.fromisoformat(str(self.subscription_end_date))
            return 'active' if end_date >= datetime.date.today() else 'expired'
        except (ValueError, TypeError):
        # If date is invalid, treat as expired
            return 'expired'

    @status.expression
    def status(cls): # noqa: N805
        """Generates the SQL expression for status queries."""
        today_str = datetime.date.today().isoformat()
        return case(
            (cls.subscription_end_date == None, 'expired'),
            (cls.subscription_end_date < today_str, 'expired'),
            else_='active'
        )

    def to_dict(self):
        """Return a dictionary representation of the model, excluding the password."""
        column_dict = {c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns if c.key != 'password'}
        column_dict['status'] = self.status # Manually add the hybrid property
        return column_dict

class Transaction(Base):
    __tablename__ = 'transaction'
    __table_args__ = {'schema': SCHEMA_NAME} if SCHEMA_NAME else {}
    transaction_id = Column(String(50), primary_key=True)
    member_name = Column(String(50), nullable=True)
    mobile_number = Column(String(10), nullable=True)
    date = Column(String(50), nullable=True)
    amount = Column(String(50), nullable=True)
    discount = Column(String(50), nullable=True)
    payment_method = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)

# Create tables in the database if they do not exist
db.init_db()
