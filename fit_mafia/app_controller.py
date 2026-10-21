import datetime
import logging
import os
import uuid

import config
from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from fit_mafia.constants import MEMBER_NOT_FOUND,INTERNAL_SERVER_ERROR
from fit_mafia.models import Member, Session, Transaction, db
from object_storage import ObjectStorageManager


def get_configured_rows_limit() -> int:
    """Reads configurable row limit from properties.ini [app] show_rows_limit with fallback."""
    try:
        val = (
            config.get_property('app', 'show_rows_limit')
            or config.get_property('app', 'pagination_limit')
            or os.getenv('SHOW_ROWS_LIMIT')
            or os.getenv('PAGINATION_LIMIT')
            or '100'
        )
        return max(1, int(val))
    except Exception:
        return 100


def login(username,password):
    try:
        presets = {
            'admin': (('admin',), 'admin', 'Admin', False, 'admin'),
            'demoadmin': (('demoadmin', '123456'), 'admin', 'Demo Admin', True, 'demoadmin'),
            'demomember': (('demomember', '123456'), 'member', 'Demo Member', True, '9551830381'),
            '9551830381': (('demomember', '123456'), 'member', 'Demo Member', True, '9551830381'),
        }

        if username in presets:
            valid_passwords, role, display_name, is_demo, username = presets[username]
            if password not in valid_passwords:
                return {'status': 'failure', 'message': 'Invalid login credentials'}
        else:
            member = db.session.query(Member).filter_by(mobile_number=username).first()
            if not member or member.password != password:
                return {'status': 'failure', 'message': 'Invalid login credentials'}
            role, is_demo = 'member', False
            display_name = (member.first_name.strip() if isinstance(member.first_name, str) and member.first_name.strip() else '') or username

        new_session_id = create_db_session(username)

        return {
            'status': 'success', 
            'message': 'valid login credentials',
            'session_data': {
                'logged_in': True,
                'username': username,
                'role': role,
                'is_demo': is_demo,
                'display_name': display_name,
                'last_active': datetime.datetime.now().isoformat(),
                'session_id': new_session_id
            }
        }
    except Exception as e:
        logging.exception(f"An unexpected error occurred during login: {e}")
        return {'status': 'error', 'message': INTERNAL_SERVER_ERROR}


def home(session, request_args=None):
    if request_args is None:
        request_args = {}

    role = session.get('role', 'member')
    username = session.get('username')
    is_demo = session.get('is_demo', False)
    current_user = {
        "username": username,
        "display_name": session.get('display_name', 'member'),
        "role": role,
        "is_demo": is_demo
    }

    default_limit = get_configured_rows_limit()

    try:
        member_page = max(1, int(request_args.get('member_page', 1)))
    except (ValueError, TypeError):
        member_page = 1

    try:
        member_limit = max(1, int(request_args.get('member_limit', default_limit)))
    except (ValueError, TypeError):
        member_limit = default_limit

    try:
        txn_page = max(1, int(request_args.get('txn_page', 1)))
    except (ValueError, TypeError):
        txn_page = 1

    try:
        txn_limit = max(1, int(request_args.get('txn_limit', default_limit)))
    except (ValueError, TypeError):
        txn_limit = default_limit

    try:
        if role == 'admin':
            member_offset = (member_page - 1) * member_limit
            all_members = db.session.query(Member).order_by(
                func.lower(func.trim(Member.first_name)).asc()
            ).limit(member_limit).offset(member_offset).all()

            try:
                total_members = int(db.session.query(Member).count())
            except (TypeError, ValueError):
                total_members = len(all_members) if isinstance(all_members, list) else 0

            try:
                today_str = datetime.date.today().isoformat()
                active_members = int(db.session.query(Member).filter(
                    Member.subscription_end_date.isnot(None),
                    Member.subscription_end_date >= today_str
                ).count())
            except Exception:
                active_members = sum(1 for m in all_members if getattr(m, 'status', None) == 'active')

            txn_offset = (txn_page - 1) * txn_limit
            transactions = db.session.query(Transaction).order_by(
                Transaction.date.desc(), Transaction.transaction_id.desc()
            ).limit(txn_limit).offset(txn_offset).all()

            try:
                total_transactions = int(db.session.query(Transaction).count())
            except (TypeError, ValueError):
                total_transactions = len(transactions) if isinstance(transactions, list) else 0

            template_data = {
                'current_user': current_user,
                'members': all_members,
                'transactions': transactions,
                'total_members': total_members,
                'active_members': active_members,
                'inactive_members': max(0, total_members - active_members),
                'member_pagination': {
                    'page': member_page,
                    'limit': member_limit,
                    'total': total_members,
                    'total_pages': max(1, (total_members + member_limit - 1) // member_limit),
                    'has_next': member_page * member_limit < total_members,
                    'has_prev': member_page > 1
                },
                'transaction_pagination': {
                    'page': txn_page,
                    'limit': txn_limit,
                    'total': total_transactions,
                    'total_pages': max(1, (total_transactions + txn_limit - 1) // txn_limit),
                    'has_next': txn_page * txn_limit < total_transactions,
                    'has_prev': txn_page > 1
                }
            }
        else:
            member = db.session.query(Member).filter_by(mobile_number=username).first()
            if not member:
                logging.warning(f"Member not found for username {username} in session. Clearing session.")
                session.clear()
                return {'status': 'failure',
                        'message': f"Member not found for username {username} in session. Clearing session."}

            display_name = (member.first_name.strip() if isinstance(member.first_name, str) and member.first_name.strip() else '') or username
            session['display_name'] = display_name
            current_user['display_name'] = display_name

            member_txn_query = db.session.query(Transaction).filter_by(mobile_number=username)
            try:
                total_member_txns = int(member_txn_query.count())
            except (TypeError, ValueError):
                total_member_txns = 0

            txn_offset = (txn_page - 1) * txn_limit
            transactions = member_txn_query.order_by(
                Transaction.date.desc(), Transaction.transaction_id.desc()
            ).limit(txn_limit).offset(txn_offset).all()

            if total_member_txns == 0 and isinstance(transactions, list):
                total_member_txns = len(transactions)

            template_data = {
                'current_user': current_user,
                'current_member': member.to_dict(),
                'transactions': transactions,
                'total_members': 1,
                'active_members': 1 if member.status == 'active' else 0,
                'inactive_members': 1 if member.status != 'active' else 0,
                'transaction_pagination': {
                    'page': txn_page,
                    'limit': txn_limit,
                    'total': total_member_txns,
                    'total_pages': max(1, (total_member_txns + txn_limit - 1) // txn_limit),
                    'has_next': txn_page * txn_limit < total_member_txns,
                    'has_prev': txn_page > 1
                }
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


def generate_transaction_id():
    return f"TXN{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"


def register_transaction(session,request):
    if session.get('role') != 'admin':
        return {'status': 'error', 'message': 'An error occurred while registering transaction.'}

    try:
        new_txn = Transaction(
            transaction_id=request.get('transaction_id') or generate_transaction_id(),
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


def update_member(session, request, file):
    mobile_number = request.get('mobile_number')

    if not (mobile_number and len(mobile_number) == 10 and mobile_number.isdigit()):
        return {'status': 'failure', 'message': 'Mobile number must be 10 digits.'}

    role = session.get('role') if session else None
    username = session.get('username') if session else None

    if role != 'admin' and username != mobile_number:
        return {'status': 'failure', 'message': 'Unauthorized', 'code': 403}

    member = db.session.query(Member).filter_by(mobile_number=mobile_number).first()
    if not member:
        return {'status': 'failure', 'message': MEMBER_NOT_FOUND, 'code': 404}

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
        member.dob = request.get('dob')
        member.gender = request.get('gender')
        member.email = request.get('email')
        member.address = request.get('address')
        if role == 'admin':
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


def update_vitals(session, request):
    role = session.get('role')
    mobile_number = request.get('mobile_number')

    if role != 'admin' and (role != 'member' or not mobile_number or session.get('username') != mobile_number):
        return {'status': 'error', 'message': 'Unauthorized', 'code': 403}

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
            member_name = (member.first_name.strip() if isinstance(member.first_name, str) and member.first_name.strip() else '') or member.mobile_number
            new_txn = Transaction(
                transaction_id=request.get('transaction_id') or generate_transaction_id(),
                member_name=member_name,
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