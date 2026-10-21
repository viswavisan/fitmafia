import datetime
import logging
import os
import uuid


def get_sample_data(member_cls, transaction_cls):
    """Returns sample members and transactions for demo sandbox."""
    today = datetime.date.today()

    sample_members = [
        member_cls(
            mobile_number='9876543210',
            first_name='Rahul Sharma',
            dob='1995-04-12',
            gender='Male',
            email='rahul.sharma@example.com',
            address='Plot 42, Jubilee Hills, Hyderabad',
            height='178',
            weight='76',
            bmi='24.0',
            subscription='Monthly',
            joining_date=(today - datetime.timedelta(days=60)).isoformat(),
            subscription_start_date=(today - datetime.timedelta(days=10)).isoformat(),
            subscription_end_date=(today + datetime.timedelta(days=20)).isoformat(),
            password='password123'
        ),
        member_cls(
            mobile_number='9876543211',
            first_name='Priya Patel',
            dob='1998-08-23',
            gender='Female',
            email='priya.patel@example.com',
            address='Road No 10, Banjara Hills, Hyderabad',
            height='165',
            weight='58',
            bmi='21.3',
            subscription='Annual',
            joining_date=(today - datetime.timedelta(days=120)).isoformat(),
            subscription_start_date=(today - datetime.timedelta(days=30)).isoformat(),
            subscription_end_date=(today + datetime.timedelta(days=335)).isoformat(),
            password='password123'
        ),
        member_cls(
            mobile_number='9876543212',
            first_name='Vikram Malhotra',
            dob='1990-11-05',
            gender='Male',
            email='vikram.m@example.com',
            address='Madhapur, Hyderabad',
            height='182',
            weight='85',
            bmi='25.7',
            subscription='Quarterly',
            joining_date=(today - datetime.timedelta(days=200)).isoformat(),
            subscription_start_date=(today - datetime.timedelta(days=120)).isoformat(),
            subscription_end_date=(today - datetime.timedelta(days=30)).isoformat(),
            password='password123'
        ),
        member_cls(
            mobile_number='9876543213',
            first_name='Ananya Desai',
            dob='2000-01-18',
            gender='Female',
            email='ananya.d@example.com',
            address='Gachibowli, Hyderabad',
            height='160',
            weight='52',
            bmi='20.3',
            subscription='Half-yearly',
            joining_date=(today - datetime.timedelta(days=45)).isoformat(),
            subscription_start_date=(today - datetime.timedelta(days=15)).isoformat(),
            subscription_end_date=(today + datetime.timedelta(days=165)).isoformat(),
            password='password123'
        ),
        member_cls(
            mobile_number='9551830381',
            first_name='Viswa',
            dob='1996-05-15',
            gender='Male',
            email='viswa@example.com',
            address='Hyderabad',
            height='175',
            weight='70',
            bmi='22.9',
            subscription='Monthly',
            joining_date=(today - datetime.timedelta(days=90)).isoformat(),
            subscription_start_date=(today - datetime.timedelta(days=5)).isoformat(),
            subscription_end_date=(today + datetime.timedelta(days=25)).isoformat(),
            password='123456'
        ),
    ]

    sample_transactions = [
        transaction_cls(
            transaction_id=str(uuid.uuid4())[:8].upper(),
            member_name='Rahul Sharma',
            mobile_number='9876543210',
            date=(today - datetime.timedelta(days=10)).isoformat(),
            amount='1500',
            discount='0',
            payment_method='UPI',
            status='Completed'
        ),
        transaction_cls(
            transaction_id=str(uuid.uuid4())[:8].upper(),
            member_name='Priya Patel',
            mobile_number='9876543211',
            date=(today - datetime.timedelta(days=30)).isoformat(),
            amount='12000',
            discount='1000',
            payment_method='Credit Card',
            status='Completed'
        ),
        transaction_cls(
            transaction_id=str(uuid.uuid4())[:8].upper(),
            member_name='Ananya Desai',
            mobile_number='9876543213',
            date=(today - datetime.timedelta(days=15)).isoformat(),
            amount='7000',
            discount='500',
            payment_method='Cash',
            status='Completed'
        ),
    ]

    return sample_members, sample_transactions


def reset_demo_db(db=None, force=False):
    """Resets the demo sandbox database.
    If force=True, drops and recreates all tables.
    If force=False, only seeds data if the demo database is currently empty.
    """
    from database import Base
    from fit_mafia.models import Member, Transaction, db as default_db

    target_db = db or default_db

    try:
        if force:
            Base.metadata.drop_all(target_db.demo_engine)
        Base.metadata.create_all(target_db.demo_engine)

        session = target_db._demo_session()
        try:
            if force or session.query(Member).count() == 0:
                if force:
                    session.query(Transaction).delete()
                    session.query(Member).delete()

                members, transactions = get_sample_data(Member, Transaction)
                session.add_all(members)
                session.add_all(transactions)
                session.commit()
                logging.info("Demo sandbox database reset and populated with sample data.")
        except Exception as e:
            session.rollback()
            logging.exception(f"Error seeding demo database: {e}")
        finally:
            session.close()
    except Exception as e:
        logging.exception(f"Error resetting demo database: {e}")


if __name__ == '__main__':
    reset_demo_db(force=True)
    print("Demo sandbox database reset successfully.")
