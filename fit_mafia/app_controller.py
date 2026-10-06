import datetime
import logging
import uuid

from dateutil.relativedelta import relativedelta

from fit_mafia.constants import MEMBER_NOT_FOUND,INTERNAL_SERVER_ERROR
from fit_mafia.models import Member, Session, Transaction, db
from object_storage import ObjectStorageManager


def login(username,password):
    try:
        admin_credentials = {'admin': 'admin'}
        
        if username in admin_credentials:
            if admin_credentials[username] == password:
                role = 'admin'
                display_name = 'Admin'
            else:
                return {'status': 'failure', 'message': 'Invalid login credentials'}
        else:
            member = db.session.query(Member).filter_by(mobile_number=username).first()
            if member and member.password == password:
                role = 'member'
                display_name = f"{member.first_name} {member.last_name}".strip() or username
            else:
                return {'status': 'failure', 'message': 'Invalid login credentials'}

        new_session_id = create_db_session(username)

        return {
            'status': 'success', 
            'message': 'valid login credentials',
            'session_data': {
                'logged_in': True,
                'username': username,
                'role': role,
                'display_name': display_name,
                'last_active': datetime.datetime.now().isoformat(),
                'session_id': new_session_id
            }
        }
    except Exception as e:
        logging.exception(f"An unexpected error occurred during login: {e}")
        return {'status': 'error', 'message': INTERNAL_SERVER_ERROR}


def home(session):
    role = session.get('role', 'member')
    username = session.get('username')
    current_user = {
        "username": username,
        "display_name": session.get('display_name', 'member'),
        "role": role
    }

    try:
        if role == 'admin':
            all_members = db.session.query(Member).all()
            total_members = len(all_members)
            active_members = sum(1 for m in all_members if m.status == 'active')
            template_data = {
                'current_user': current_user,
                'members': all_members,
                'transactions': db.session.query(Transaction).all(),
                'total_members': total_members,
                'active_members': active_members,
                'inactive_members': total_members - active_members
            }
        else:
            member = db.session.query(Member).filter_by(mobile_number=username).first()
            if not member:
                logging.warning(f"Member not found for username {username} in session. Clearing session.")
                session.clear()
                return {'status': 'failure',
                        'message': f"Member not found for username {username} in session. Clearing session."}

            template_data = {
                'current_user': current_user,
                'current_member': member.to_dict(),
                'transactions': db.session.query(Transaction).filter_by(mobile_number=username).all(),
                'total_members': 1,
                'active_members': 1 if member.status == 'active' else 0,
                'inactive_members': 1 if member.status != 'active' else 0,
            }

        return {'status': 'success', 'template_data': template_data}

    except Exception as e:
        db.session.rollback()
        logging.exception(f"Error fetching homepage data for role {role}: {e}")
        return {'status': 'error', 'message': INTERNAL_SERVER_ERROR}


def logout(session):
    session_id = session.get('session_id')
    if session_id:
        try:
            record = db.session.query(Session).filter_by(session_id=session_id).first()
            if record:
                record.end_time = str(datetime.datetime.now())
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.exception(f"Error updating session end_time on logout: {e}")
    session.clear()


def register_transaction(session,request):
    if session.get('role') != 'admin':
        return {'status': 'error', 'message': 'An error occurred while registering transaction.'}

    try:
        new_txn = Transaction(
            transaction_id=request.get('transaction_id') or f"TXN{str(uuid.uuid4())[:8].upper()}",
            member_name=request.get('member_name'),
            mobile_number=request.get('mobile_number'),
            date=request.get('date'),
            amount=request.get('amount'),
            payment_method=request.get('payment_method'),
            status=request.get('status')
        )
        db.session.merge(new_txn)
        db.session.commit()
        return {'status': 'success', 'message': 'Transaction registered successfully.'}
    except Exception as e:
        db.session.rollback()
        logging.exception(f"Error registering transaction: {e}")
        return {'status': 'error', 'message': INTERNAL_SERVER_ERROR}


def print_receipt(transaction_id,session):
    try:
        txn = db.session.query(Transaction).filter_by(transaction_id=transaction_id).first()
        if not txn:
            return {'status': 'failure', 'message': 'Transaction not found.'}

        if session.get('role') == 'member' and session.get('username') != txn.mobile_number:
            return {'status': 'failure', 'message': 'Unauthorized to view this receipt.'}

        member = db.session.query(Member).filter_by(mobile_number=txn.mobile_number).first()
        return {'status': 'success', 'template_data': {'txn': txn, 'member': member}}

    except Exception as e:
        logging.exception(f"Error generating receipt for transaction {transaction_id}: {e}")
        return {'status': 'error', 'message': INTERNAL_SERVER_ERROR}


def register_member(session,request,file):
    role = session.get('role')
    mobile_number = request.get('mobile_number')

    if not (mobile_number and len(mobile_number) == 10 and mobile_number.isdigit()):
        return {'status': 'failure', 'message': 'Mobile number must be 10 digits.'}

    if role != 'admin' and (role != 'member' or session.get('username') != mobile_number):
        return {'status': 'failure', 'message': 'Unauthorized'}

    if db.session.query(Member).filter_by(mobile_number=mobile_number).first():
        return {'status': 'failure', 'message': "mobile number already exists."}

    upload_result = None
    if file and file.filename != '':
        storage_manager = ObjectStorageManager()
        file_ext = file.filename.split('.')[-1]
        filename = f"{mobile_number}_photo.{file_ext}"
        upload_result = storage_manager.upload_file(file, filename)
        if "Error" in upload_result:
            return {'status': 'error', 'message': upload_result}

    try:
        new_member = Member(
            mobile_number=mobile_number,
            first_name=request.get('first_name'),
            last_name=request.get('last_name'),
            dob=request.get('dob'),
            gender=request.get('gender'),
            email=request.get('email'),
            address=request.get('address'),
            joining_date=request.get('joining_date') or datetime.date.today().isoformat(),
            photo=upload_result,
            password=request.get('password')
        )
        db.session.add(new_member)
        db.session.commit()
        return {'status':'success', 'message': 'Member registered successfully.'}

    except Exception as e:
        db.session.rollback()
        logging.exception(f"Error registering member: {e}")
        return {'status': 'error', 'message': INTERNAL_SERVER_ERROR}


def update_member(_, request, file):
    mobile_number = request.get('mobile_number')

    if not (mobile_number and len(mobile_number) == 10 and mobile_number.isdigit()):
        return {'status': 'failure', 'message': 'Mobile number must be 10 digits.'}

    member = db.session.query(Member).filter_by(mobile_number=mobile_number).first()
    upload_result = None
    if file and file.filename != '':
        storage_manager = ObjectStorageManager()
        file_ext = file.filename.split('.')[-1]
        filename = f"{mobile_number}_photo.{file_ext}"
        upload_result = storage_manager.upload_file(file, filename)
        if "Error" in upload_result:
            return {'status': 'error', 'message': upload_result}

    try:
        member.first_name = request.get('first_name')
        member.last_name = request.get('last_name')
        member.dob = request.get('dob')
        member.gender = request.get('gender')
        member.email = request.get('email')
        member.address = request.get('address')
        member.joining_date = request.get('joining_date') or member.joining_date
        if upload_result:
            member.photo = upload_result

        db.session.commit()
        return {'status': 'success', 'message': 'Member updated successfully.'}

    except Exception as e:
        db.session.rollback()
        logging.exception(f"Error updating member for mobile number {mobile_number}: {e}")
        return {'status': 'error', 'message': INTERNAL_SERVER_ERROR}


def delete_member(session, mobile_number):
    if session.get('role') != 'admin':
        return {'status': 'error', 'message': 'Unauthorized', 'code': 403}

    if not (mobile_number and str(mobile_number).strip()):
        return {'status': 'error', 'message': 'Mobile number is required', 'code': 400}

    mobile_number = str(mobile_number).strip()

    try:
        member = db.session.query(Member).filter_by(mobile_number=mobile_number).first()
        if not member:
            return {'status': 'failure', 'message': MEMBER_NOT_FOUND, 'code': 404}

        db.session.query(Transaction).filter_by(mobile_number=mobile_number).delete()
        db.session.delete(member)
        db.session.commit()
        return {'status': 'success', 'message': f'Member {mobile_number} deleted successfully.', 'code': 200}

    except Exception as e:
        db.session.rollback()
        logging.exception(f"Error deleting member {mobile_number}: {e}")
        return {'status': 'error', 'message': INTERNAL_SERVER_ERROR, 'code': 500}


def update_vitals(session,request):
    if session.get('role') != 'admin':
        return {'status':'error','message':'Unauthorized','code':403}

    mobile_number = request.get('mobile_number')
    if not mobile_number:
        return {'status': 'error', 'message': 'Mobile number required', 'code': 400}

    try:
        member = db.session.query(Member).filter_by(mobile_number=mobile_number).first()
        if member:
            member.height = request.get('height')
            member.weight = request.get('weight')
            member.bmi = request.get('bmi')
            db.session.commit()
            return {'status': 'success', 'message': True, 'code': 200}
        return  {'status': 'error', 'message': MEMBER_NOT_FOUND, 'code': 404}

    except Exception as e:
        db.session.rollback()
        logging.exception(f"Error updating vitals: {e}")
        return {'status': 'error', 'message': INTERNAL_SERVER_ERROR, 'code': 500}

def renew_subscription(session,request):
    if session.get('role') != 'admin':
        return {'status': 'error', 'message': "Unauthorized", 'code': 403}

    mobile_number = request.get('mobile_number')
    subscription = request.get('subscription')
    subscription_start_date = request.get('subscription_start_date')

    if not all([mobile_number, subscription, subscription_start_date]):
        return {'status': 'error', 'message': "Missing required parameters", 'code': 400}

    try:
        member = db.session.query(Member).filter_by(mobile_number=mobile_number).first()
        if not member:
            return {'status': 'error', 'message': MEMBER_NOT_FOUND, 'code': 404}

        member.subscription = subscription
        member.subscription_start_date = subscription_start_date

        member.subscription_end_date = request.get('subscription_end_date') or calculate_end_date(
            subscription_start_date, subscription)

        amount = request.get('amount')
        payment_method = request.get('payment_method')
        if amount and payment_method:
            # create_transaction(member, amount, request.get('discount'), payment_method)
            new_txn = Transaction(
                transaction_id=f"{member.first_name or ''} {member.last_name or ''}".strip() or member.mobile_number,
                member_name=f"{member.first_name or ''} {member.last_name or ''}".strip() or member.mobile_number,
                mobile_number=member.mobile_number,
                date=datetime.date.today().isoformat(),
                amount=amount,
                discount=request.get('discount'),
                payment_method=payment_method,
                status="Completed"
            )

            db.session.add(new_txn)

        db.session.commit()
        return {'status': 'success', 'message': True, 'code': 200}

    except Exception as e:
        db.session.rollback()
        logging.exception(f"Error renewing subscription: {e}")
        return {'status': 'error', 'message': INTERNAL_SERVER_ERROR, 'code': 500}

def get_member(mobile_number,session):
    try:
        if session.get('role') == 'member' and session.get('username') != mobile_number:
            return {'status': 'error', 'message': "Unauthorized", 'code': 403}

        member = db.session.query(Member).filter_by(mobile_number=mobile_number).first()
        if member:
            return {'status': 'success', 'message': member, 'code': 200}
        return {'status': 'error', 'message': MEMBER_NOT_FOUND, 'code': 404}
    except Exception as e:
        logging.exception(f"API error getting member {mobile_number}: {e}")
        return {'status': 'error', 'message': INTERNAL_SERVER_ERROR, 'code': 500}


#support scripts


def calculate_end_date(start_date_str, plan):
    if not start_date_str or not plan:
        return None
    try:
        start_date = datetime.date.fromisoformat(start_date_str)
        months = int(plan.split(' ')[0])
        end_date = start_date + relativedelta(months=months)
        return end_date.isoformat()
    except (ValueError, TypeError) as e:
        logging.exception(f"Error calculating end date for start_date={start_date_str}, plan={plan}: {e}")
        return None


def create_db_session(username):
    """Creates and records a new session in the database."""
    try:
        new_session_id = str(uuid.uuid4())
        new_record = Session(session_id=new_session_id,
                             start_time=str(datetime.datetime.now()),
                             user_name=username)
        db.session.add(new_record)
        db.session.commit()
        return new_session_id
    except Exception as e:
        db.session.rollback()
        logging.exception(f"Error recording new session for user {username}: {e}")
        return None


def handle_session_timeout(now,session):
    if 'last_active' not in session:
        return False
    last_active = datetime.datetime.fromisoformat(session['last_active'])
    if now - last_active > datetime.timedelta(minutes=30):  # increased to 30 mins
        session_id = session.get('session_id')
        try:
            record = db.session.query(Session).filter_by(session_id=session_id).first()
            if record:
                record.end_time = str(now)
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.exception(f"Error updating session end_time on timeout: {e}")

        session.clear()
        return True
    return False