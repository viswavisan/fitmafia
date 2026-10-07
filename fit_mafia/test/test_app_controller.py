import pytest
import datetime
from unittest.mock import patch, MagicMock
from fit_mafia.app_controller import (
    home, logout, register_transaction, print_receipt,
    register_member, update_member, delete_member, update_vitals, renew_subscription, get_member, login,
    calculate_end_date, handle_session_timeout, create_db_session
)
from fit_mafia.constants import INTERNAL_SERVER_ERROR, MEMBER_NOT_FOUND
from fit_mafia.test.conftest import app
from fit_mafia.models import Member, Session, Transaction


# --- LOGIN TESTS ---

@pytest.mark.parametrize("username, password, expected_status, expected_role", [
    ('admin', 'admin', 'success', 'admin'),
    ('admin', 'wrong_password', 'failure', None),
])
@patch('fit_mafia.app_controller.create_db_session')
@patch('fit_mafia.app_controller.db.session')
def test_login_admin(mock_db_session, mock_create_db_session, username, password, expected_status, expected_role):
    with app.test_request_context():
        result = login(username, password)

        assert result['status'] == expected_status
        if expected_status == 'success':
            assert result['session_data']['role'] == expected_role
            assert result['session_data'].get('logged_in') is True
            mock_create_db_session.assert_called_once()
        else:
            assert 'role' not in result.get('session_data', {})


@pytest.mark.parametrize("username, password, db_returns_member, member_password, expected_status", [
    ('9999999999', 'password123', True, 'password123', 'success'),
    ('9999999999', 'wrong_password', True, 'password123', 'failure'),
    ('9999999999', 'password123', False, None, 'failure'),
])
@patch('fit_mafia.app_controller.create_db_session')
@patch('fit_mafia.app_controller.db.session')
def test_login_member(mock_db_session, mock_create_db_session, username, password, db_returns_member, member_password,
                      expected_status):
    with app.test_request_context():
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value

        if db_returns_member:
            mock_member = MagicMock(spec=Member)
            mock_member.password = member_password
            mock_member.first_name = 'John'
            mock_member.last_name = 'Doe'
            mock_filter.first.return_value = mock_member
        else:
            mock_filter.first.return_value = None

        result = login(username, password)

        assert result['status'] == expected_status
        if expected_status == 'success':
            assert result['session_data']['role'] == 'member'
            assert result['session_data'].get('logged_in') is True
            mock_create_db_session.assert_called_once()
        else:
            assert 'role' not in result.get('session_data', {})


@patch('fit_mafia.app_controller.db.session')
def test_login_exception(mock_db_session):
    with app.test_request_context():
        mock_db_session.query.side_effect = Exception("Database error")
        result = login('some_user', 'some_password')
        assert result == {'status': 'error', 'message': INTERNAL_SERVER_ERROR}


# --- HOME TESTS ---

@patch('fit_mafia.app_controller.db.session')
def test_home_admin(mock_db_session):
    with app.test_request_context():
        from flask import session
        session['role'] = 'admin'
        session['username'] = 'admin'

        mock_member = MagicMock(spec=Member)
        mock_member.status = 'active'

        mock_query = mock_db_session.query.return_value
        mock_query.all.return_value = [mock_member]

        result = home(session)
        assert result['status'] == 'success'
        assert result['template_data']['total_members'] == 1
        assert result['template_data']['active_members'] == 1

@patch('fit_mafia.app_controller.db.session')
def test_home_member_success(mock_db_session):
    with app.test_request_context():
        from flask import session
        session['role'] = 'member'
        session['username'] = '9999999999'
        
        mock_member = MagicMock(spec=Member)
        mock_member.status = 'active'
        mock_member.to_dict.return_value = {'name': 'Test'}
        
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_member
        mock_filter.all.return_value = []

        result = home(session)
        assert result['status'] == 'success'
        assert result['template_data']['current_member']['name'] == 'Test'

@patch('fit_mafia.app_controller.db.session')
def test_home_member_not_found(mock_db_session):
    with app.test_request_context():
        from flask import session
        session['role'] = 'member'
        session['username'] = '9999999999'
        
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = None # Simulate member not found
        
        result = home(session)
        assert result['status'] == 'failure'
        assert "Member not found" in result['message']

@patch('fit_mafia.app_controller.db.session')
def test_home_exception(mock_db_session):
    with app.test_request_context():
        mock_db_session.query.side_effect = Exception("Database error")
        result = home({})
        assert result == {'status': 'error', 'message': INTERNAL_SERVER_ERROR}

# --- LOGOUT TESTS ---

@patch('fit_mafia.app_controller.db.session')
def test_logout(mock_db_session):
    with app.test_request_context():
        from flask import session
        session['session_id'] = 'session123'

        mock_record = MagicMock(spec=Session)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_record

        logout(session)
        assert 'session_id' not in session
        assert mock_record.end_time is not None
        mock_db_session.commit.assert_called_once()

@patch('fit_mafia.app_controller.logging')
@patch('fit_mafia.app_controller.db.session')
def test_logout_exception(mock_db_session, mock_logging):
    with app.test_request_context():
        from flask import session
        session['session_id'] = 'session123'

        mock_record = MagicMock(spec=Session)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_record

        # Simulate a database error on commit
        mock_db_session.commit.side_effect = Exception("DB Error")

        logout(session)

        mock_db_session.rollback.assert_called_once()
        mock_logging.exception.assert_called_once()
        assert 'session_id' not in session


# --- TRANSACTION TESTS ---

@patch('fit_mafia.app_controller.db.session')
def test_register_transaction_admin(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request_data = {
            'transaction_id': 'TXN123',
            'member_name': 'Test Member',
            'mobile_number': '9876543210',
            'date': '2023-01-01',
            'amount': '500',
            'payment_method': 'Credit Card',
            'status': 'Completed'
        }

        result = register_transaction(mock_session, mock_request_data)
        assert result['status'] == 'success'
        mock_db_session.merge.assert_called_once()
        mock_db_session.commit.assert_called_once()

@patch('fit_mafia.app_controller.db.session')
def test_register_transaction_unauthorized(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'member'}

        result = register_transaction(mock_session, {})
        assert result['status'] == 'error'
        mock_db_session.merge.assert_not_called()

@patch('fit_mafia.app_controller.logging')
@patch('fit_mafia.app_controller.db.session')
def test_register_transaction_exception(mock_db_session, mock_logging):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request_data = {
            'transaction_id': 'TXN123',
            'member_name': 'Test Member',
            'mobile_number': '9876543210',
            'date': '2023-01-01',
            'amount': '500',
            'payment_method': 'Credit Card',
            'status': 'Completed'
        }
        
        mock_db_session.merge.side_effect = Exception("DB Merge Error")

        result = register_transaction(mock_session, mock_request_data)

        assert result['status'] == 'error'
        assert result['message'] == INTERNAL_SERVER_ERROR
        mock_db_session.rollback.assert_called_once()
        mock_logging.exception.assert_called_once()


# --- PRINT RECEIPT TESTS ---

@patch('fit_mafia.app_controller.db.session')
def test_print_receipt_success(mock_db_session):
    with app.test_request_context():
        from flask import session
        session['role'] = 'admin'

        mock_txn = MagicMock(spec=Transaction)
        mock_txn.mobile_number = '9999999999'

        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_txn

        result = print_receipt('TXN123',session)
        assert result['status'] == 'success'

@patch('fit_mafia.app_controller.db.session')
def test_print_receipt_not_found(mock_db_session):
    with app.test_request_context():
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = None  # Simulate transaction not found

        result = print_receipt('TXN_NOT_FOUND',{})
        assert result['status'] == 'failure'
        assert result['message'] == 'Transaction not found.'

@patch('fit_mafia.app_controller.db.session')
def test_print_receipt_unauthorized(mock_db_session):
    with app.test_request_context():
        from flask import session
        session['role'] = 'member'
        session['username'] = '1111111111'  # Logged in user

        mock_txn = MagicMock(spec=Transaction)
        mock_txn.mobile_number = '9999999999'  # Receipt belongs to a different user

        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_txn

        result = print_receipt('TXN123',session)
        assert result['status'] == 'failure'
        assert result['message'] == 'Unauthorized to view this receipt.'

@patch('fit_mafia.app_controller.db.session')
def test_print_receipt_exception(mock_db_session):
    with app.test_request_context():
        mock_db_session.query.side_effect = Exception("DB Error")
        result = print_receipt('TXN123',{})
        assert result['status'] == 'error'
        assert result['message'] == INTERNAL_SERVER_ERROR


# --- MEMBER TESTS ---

@patch('fit_mafia.app_controller.ObjectStorageManager')
@patch('fit_mafia.app_controller.db.session')
def test_register_member_success(mock_db_session, mock_storage_manager):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request_data = {
            'mobile_number': '1234567890',
            'first_name': 'John',
            'last_name': 'Doe',
            'password': 'password123'
        }
        mock_request = MagicMock()
        mock_request.get.side_effect = lambda key: mock_request_data.get(key)
        
        mock_file = MagicMock()
        mock_file.filename = ''

        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = None # Member doesn't exist

        result = register_member(mock_session, mock_request, mock_file)
        assert result['status'] == 'success'
        assert 'registered' in result['message']
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

@patch('fit_mafia.app_controller.ObjectStorageManager')
@patch('fit_mafia.app_controller.db.session')
def test_update_member_success(mock_db_session, mock_storage_manager):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mobile_number = '1234567890'
        mock_request_data = {
            'mobile_number': mobile_number,
            'first_name': 'John Updated',
            'last_name': 'Doe Updated',
        }
        mock_request = MagicMock()
        mock_request.get.side_effect = lambda key: mock_request_data.get(key)
        
        mock_file = MagicMock()
        mock_file.filename = ''

        # Simulate existing member
        mock_member = Member(mobile_number=mobile_number, first_name='John', last_name='Doe')
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_member

        result = update_member(mock_session, mock_request, mock_file)
        
        assert result['status'] == 'success'
        assert 'updated' in result['message']
        assert mock_member.first_name == 'John Updated'
        assert mock_member.last_name == 'Doe Updated'
        mock_db_session.add.assert_not_called() # Should not add a new member
        mock_db_session.commit.assert_called_once()

@patch('fit_mafia.app_controller.ObjectStorageManager')
@patch('fit_mafia.app_controller.db.session')
def test_register_member_with_file_upload(mock_db_session, mock_storage_manager):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mobile_number = '1234567890'
        mock_request_data = {
            'mobile_number': mobile_number,
            'first_name': 'Jane',
            'last_name': 'Doe',
            'password': 'password123'
        }
        mock_request = MagicMock()
        mock_request.get.side_effect = lambda key: mock_request_data.get(key)
        
        mock_file = MagicMock()
        mock_file.filename = 'test_photo.png'
        
        # Mock the storage manager's upload_file to return a filename
        mock_storage_instance = mock_storage_manager.return_value
        mock_storage_instance.upload_file.return_value = f"https://example.com/{mobile_number}_photo.png"

        # Test creating a new member with a photo
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = None

        result = register_member(mock_session, mock_request, mock_file)
        assert result['status'] == 'success'
        
        mock_db_session.add.assert_called_once()
        added_member = mock_db_session.add.call_args[0][0]
        assert added_member.photo == f"https://example.com/{mobile_number}_photo.png"
        mock_db_session.commit.assert_called_once()

@patch('fit_mafia.app_controller.ObjectStorageManager')
@patch('fit_mafia.app_controller.db.session')
def test_update_member_with_file_upload(mock_db_session, mock_storage_manager):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mobile_number = '1234567890'
        mock_request_data = {
            'mobile_number': mobile_number,
        }
        mock_request = MagicMock()
        mock_request.get.side_effect = lambda key: mock_request_data.get(key)
        
        mock_file = MagicMock()
        mock_file.filename = 'new_photo.png'
        
        mock_storage_instance = mock_storage_manager.return_value
        mock_storage_instance.upload_file.return_value = "https://example.com/new_photo.png"

        mock_existing_member = Member(mobile_number=mobile_number, first_name='Jane', photo='old_photo.png')
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_existing_member
        
        result = update_member(mock_session, mock_request, mock_file)
        assert result['status'] == 'success'
        assert mock_existing_member.photo == "https://example.com/new_photo.png"
        mock_db_session.commit.assert_called_once()


@patch('fit_mafia.app_controller.db.session')
def test_register_member_unauthorized(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'member', 'username': '1111111111'}
        mock_request_data = {'mobile_number': '9999999999'} # Different mobile number
        mock_request = MagicMock()
        mock_request.get.side_effect = lambda key: mock_request_data.get(key)
        mock_file = MagicMock()
        mock_file.filename = ''

        result = register_member(mock_session, mock_request, mock_file)
        assert result['status'] == 'failure'
        assert result['message'] == 'Unauthorized'

@patch('fit_mafia.app_controller.db.session')
def test_register_member_already_exists(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mobile_number = '1234567890'
        mock_request_data = {'mobile_number': mobile_number}
        mock_request = MagicMock()
        mock_request.get.side_effect = lambda key: mock_request_data.get(key)
        mock_file = MagicMock()
        mock_file.filename = ''

        # Simulate member already exists
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = MagicMock(spec=Member)

        result = register_member(mock_session, mock_request, mock_file)
        assert result['status'] == 'failure'
        assert "mobile number already exists." in result['message']

@patch('fit_mafia.app_controller.logging')
@patch('fit_mafia.app_controller.db.session')
def test_register_member_exception(mock_db_session, mock_logging):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request_data = {
            'mobile_number': '1234567890',
        }
        mock_request = MagicMock()
        mock_request.get.side_effect = lambda key: mock_request_data.get(key)
        mock_file = MagicMock()
        mock_file.filename = ''

        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = None # Member doesn't exist

        mock_db_session.add.side_effect = Exception("DB Add Error")

        result = register_member(mock_session, mock_request, mock_file)
        assert result['status'] == 'error'
        assert result['message'] == INTERNAL_SERVER_ERROR
        mock_db_session.rollback.assert_called_once()
        mock_logging.exception.assert_called_once()

@patch('fit_mafia.app_controller.ObjectStorageManager')
def test_register_member_upload_error(mock_storage_manager):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request_data = {'mobile_number': '1234567890'}
        mock_request = MagicMock()
        mock_request.get.side_effect = lambda key: mock_request_data.get(key)
        mock_file = MagicMock()
        mock_file.filename = 'test.jpg'

        mock_storage_instance = mock_storage_manager.return_value
        mock_storage_instance.upload_file.return_value = "Error: Upload failed"

        result = register_member(mock_session, mock_request, mock_file)
        assert result['status'] == 'error'
        assert "Error: Upload failed" in result['message']

@patch('fit_mafia.app_controller.ObjectStorageManager')
@patch('fit_mafia.app_controller.db.session')
def test_update_member_upload_error(mock_db_session, mock_storage_manager):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mobile_number = '1234567890'
        mock_request_data = {'mobile_number': mobile_number}
        mock_request = MagicMock()
        mock_request.get.side_effect = lambda key: mock_request_data.get(key)
        mock_file = MagicMock()
        mock_file.filename = 'test.jpg'

        mock_storage_instance = mock_storage_manager.return_value
        mock_storage_instance.upload_file.return_value = "Error: Upload failed"

        mock_existing_member = Member(mobile_number=mobile_number)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_existing_member

        result = update_member(mock_session, mock_request, mock_file)
        assert result['status'] == 'error'
        assert "Error: Upload failed" in result['message']

@patch('fit_mafia.app_controller.logging')
@patch('fit_mafia.app_controller.db.session')
def test_update_member_exception(mock_db_session, mock_logging):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mobile_number = '1234567890'
        mock_request_data = {'mobile_number': mobile_number}
        mock_request = MagicMock()
        mock_request.get.side_effect = lambda key: mock_request_data.get(key)
        mock_file = MagicMock()
        mock_file.filename = ''

        mock_existing_member = Member(mobile_number=mobile_number)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_existing_member
        
        mock_db_session.commit.side_effect = Exception("DB Commit Error")

        result = update_member(mock_session, mock_request, mock_file)
        assert result['status'] == 'error'
        assert result['message'] == INTERNAL_SERVER_ERROR
        mock_db_session.rollback.assert_called_once()
        mock_logging.exception.assert_called_once()


@patch('fit_mafia.app_controller.db.session')
def test_update_vitals_success(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request_data = {
            'mobile_number': '9999999999',
            'height': '180',
            'weight': '75',
            'bmi': '23.1'
        }

        mock_member = MagicMock(spec=Member)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_member

        result = update_vitals(mock_session, mock_request_data)
        assert result['status'] == 'success'
        mock_db_session.commit.assert_called_once()
        assert mock_member.height == '180'
        assert mock_member.weight == '75'
        assert mock_member.bmi == '23.1'

def test_update_vitals_unauthorized():
    with app.test_request_context():
        mock_session = {'role': 'member'} # Non-admin user
        result = update_vitals(mock_session, {})
        assert result['status'] == 'error'
        assert result['message'] == 'Unauthorized'
        assert result['code'] == 403

@patch('fit_mafia.app_controller.db.session')
def test_update_vitals_missing_mobile(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request_data = {
            'height': '180',
            'weight': '75',
            'bmi': '23.1'
        }

        result = update_vitals(mock_session, mock_request_data)
        assert result['status'] == 'error'
        assert result['message'] == 'Mobile number required'
        assert result['code'] == 400

@patch('fit_mafia.app_controller.db.session')
def test_update_vitals_member_not_found(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request_data = {'mobile_number': '0000000000'}

        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = None # Member not found

        result = update_vitals(mock_session, mock_request_data)
        assert result['status'] == 'error'
        assert result['message'] == MEMBER_NOT_FOUND
        assert result['code'] == 404

@patch('fit_mafia.app_controller.logging')
@patch('fit_mafia.app_controller.db.session')
def test_update_vitals_exception(mock_db_session, mock_logging):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request_data = {'mobile_number': '9999999999'}

        mock_member = MagicMock(spec=Member)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_member

        mock_db_session.commit.side_effect = Exception("DB Commit Error")

        result = update_vitals(mock_session, mock_request_data)
        assert result['status'] == 'error'
        assert result['message'] == INTERNAL_SERVER_ERROR
        assert result['code'] == 500
        mock_db_session.rollback.assert_called_once()
        mock_logging.exception.assert_called_once()


# --- RENEW SUBSCRIPTION TESTS ---

@patch('fit_mafia.app_controller.db.session')
def test_renew_subscription_success(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        
        mock_request = MagicMock()
        
        request_data = {
            'mobile_number': '9999999999',
            'subscription': '1 Month',
            'subscription_start_date': '2023-01-01',
            'subscription_end_date': '2023-02-01',
            'amount': '1000',
            'payment_method': 'Cash',
            'discount': '10'
        }
        
        mock_request.get.side_effect = lambda key: request_data.get(key)
        mock_request.form.get.side_effect = lambda key: request_data.get(key)

        mock_member = MagicMock(spec=Member)
        mock_member.first_name = "John"
        mock_member.last_name = "Doe"
        mock_member.mobile_number = "9999999999"
        
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_member

        result = renew_subscription(mock_session, mock_request)
        
        assert result['status'] == 'success'
        
        # Verify that a transaction was added to the session
        mock_db_session.add.assert_called_once()
        added_object = mock_db_session.add.call_args[0][0]
        assert isinstance(added_object, Transaction)
        assert added_object.transaction_id.startswith('TXN')
        assert added_object.amount == '1000'
        assert added_object.payment_method == 'Cash'

        mock_db_session.commit.assert_called_once()


@patch('fit_mafia.app_controller.db.session')
def test_renew_subscription_with_dict(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        request_dict = {
            'mobile_number': '9999999999',
            'subscription': '1 Month',
            'subscription_start_date': '2023-01-01',
            'subscription_end_date': '2023-02-01',
            'amount': '1500',
            'payment_method': 'UPI',
            'discount': '0'
        }

        mock_member = MagicMock(spec=Member)
        mock_member.first_name = "Jane"
        mock_member.last_name = "Smith"
        mock_member.mobile_number = "9999999999"

        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_member

        result = renew_subscription(mock_session, request_dict)

        assert result['status'] == 'success'
        assert result['code'] == 200
        mock_db_session.add.assert_called_once()
        added_object = mock_db_session.add.call_args[0][0]
        assert isinstance(added_object, Transaction)
        assert added_object.amount == '1500'
        assert added_object.payment_method == 'UPI'
        mock_db_session.commit.assert_called_once()



def test_renew_subscription_unauthorized():
    with app.test_request_context():
        mock_session = {'role': 'member'}
        mock_request = MagicMock()

        result = renew_subscription(mock_session, mock_request)
        assert result['status'] == 'error'
        assert result['message'] == "Unauthorized"
        assert result['code'] == 403

def test_renew_subscription_missing_params():
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request = MagicMock()
        mock_request.get.return_value = None
        mock_request.form.get.return_value = None

        result = renew_subscription(mock_session, mock_request)
        assert result['status'] == 'error'
        assert result['message'] == "Missing required parameters"
        assert result['code'] == 400

@patch('fit_mafia.app_controller.db.session')
def test_renew_subscription_member_not_found(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request = MagicMock()
        request_data = {
            'mobile_number': '12345',
            'subscription': '1 Month',
            'subscription_start_date': '2023-01-01'
        }
        mock_request.get.side_effect = lambda key: request_data.get(key)
        mock_request.form.get.side_effect = lambda key: request_data.get(key)

        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = None

        result = renew_subscription(mock_session, mock_request)
        assert result['status'] == 'error'
        assert result['message'] == MEMBER_NOT_FOUND
        assert result['code'] == 404

@patch('fit_mafia.app_controller.logging')
@patch('fit_mafia.app_controller.db.session')
def test_renew_subscription_exception(mock_db_session, mock_logging):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mock_request = MagicMock()
        request_data = {
            'mobile_number': '12345',
            'subscription': '1 Month',
            'subscription_start_date': '2023-01-01'
        }
        mock_request.get.side_effect = lambda key: request_data.get(key)
        mock_request.form.get.side_effect = lambda key: request_data.get(key)

        mock_member = MagicMock(spec=Member)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_member

        mock_db_session.commit.side_effect = Exception("DB Commit Error")

        result = renew_subscription(mock_session, mock_request)
        assert result['status'] == 'error'
        assert result['message'] == INTERNAL_SERVER_ERROR
        assert result['code'] == 500
        mock_db_session.rollback.assert_called_once()
        mock_logging.exception.assert_called_once()


# --- GET MEMBER TESTS ---

@patch('fit_mafia.app_controller.db.session')
def test_get_member_success(mock_db_session):
    with app.test_request_context():
        from flask import session
        session['role'] = 'admin'

        mock_member = MagicMock(spec=Member)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_member

        result = get_member('9999999999', session)
        assert result['status'] == 'success'
        assert result['message'] == mock_member

@patch('fit_mafia.app_controller.db.session')
def test_get_member_unauthorized(mock_db_session):
    with app.test_request_context():
        from flask import session
        session['role'] = 'member'
        session['username'] = '1111111111'  # Logged in user

        # This test doesn't need the database to be called, but we mock it for consistency
        result = get_member('9999999999', session) # Trying to access a different member's data
        
        assert result['status'] == 'error'
        assert result['message'] == "Unauthorized"
        assert result['code'] == 403

@patch('fit_mafia.app_controller.db.session')
def test_get_member_not_found(mock_db_session):
    with app.test_request_context():
        from flask import session
        session['role'] = 'admin' # Admin can search for anyone

        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = None # Simulate member not found

        result = get_member('0000000000', session)
        assert result['status'] == 'error'
        assert result['message'] == MEMBER_NOT_FOUND
        assert result['code'] == 404

@patch('fit_mafia.app_controller.logging')
@patch('fit_mafia.app_controller.db.session')
def test_get_member_exception(mock_db_session, mock_logging):
    with app.test_request_context():
        from flask import session
        session['role'] = 'admin'

        mock_db_session.query.side_effect = Exception("DB Error")

        result = get_member('9999999999', session)
        assert result['status'] == 'error'
        assert result['message'] == INTERNAL_SERVER_ERROR
        assert result['code'] == 500
        mock_logging.exception.assert_called_once()


# --- SUPPORT SCRIPT TESTS ---

def test_calculate_end_date_success():
    assert calculate_end_date('2023-01-15', '3 Months') == '2023-04-15'
    assert calculate_end_date('2023-12-01', '1 Month') == '2024-01-01'

@patch('fit_mafia.app_controller.logging')
def test_calculate_end_date_invalid_plan(mock_logging):
    assert calculate_end_date('2023-01-15', 'invalid plan') is None
    mock_logging.exception.assert_called_once()

@pytest.mark.parametrize("start_date, plan", [
    (None, '1 Month'),
    ('', '1 Month'),
    ('2023-01-15', None),
    ('2023-01-15', ''),
])
def test_calculate_end_date_missing_input(start_date, plan):
    assert calculate_end_date(start_date, plan) is None

def test_handle_session_timeout_no_last_active():
    with app.test_request_context():
        from flask import session
        session.clear()
        assert handle_session_timeout(datetime.datetime.now(),session) is False

def test_handle_session_timeout_not_expired():
    with app.test_request_context():
        from flask import session
        now = datetime.datetime.now()
        session['last_active'] = now.isoformat()
        assert handle_session_timeout(now,session) is False

@patch('fit_mafia.app_controller.db.session')
def test_handle_session_timeout_expired_success(mock_db_session):
    with app.test_request_context():
        from flask import session
        now = datetime.datetime.now()
        past_time = now - datetime.timedelta(minutes=31)
        session['last_active'] = past_time.isoformat()
        session['session_id'] = 'expired_session'
        
        mock_record = MagicMock(spec=Session)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_record

        assert handle_session_timeout(now,session) is True
        assert 'last_active' not in session
        mock_db_session.commit.assert_called_once()

@patch('fit_mafia.app_controller.db.session')
def test_handle_session_timeout_expired_no_record(mock_db_session):
    with app.test_request_context():
        from flask import session
        now = datetime.datetime.now()
        past_time = now - datetime.timedelta(minutes=31)
        session['last_active'] = past_time.isoformat()
        session['session_id'] = 'expired_session_no_record'

        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = None # No record found

        assert handle_session_timeout(now,session) is True
        assert 'last_active' not in session
        mock_db_session.commit.assert_not_called()

@patch('fit_mafia.app_controller.logging')
@patch('fit_mafia.app_controller.db.session')
def test_handle_session_timeout_expired_db_exception(mock_db_session, mock_logging):
    with app.test_request_context():
        from flask import session
        now = datetime.datetime.now()
        past_time = now - datetime.timedelta(minutes=31)
        session['last_active'] = past_time.isoformat()
        session['session_id'] = 'expired_session_db_error'

        mock_record = MagicMock(spec=Session)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_record

        mock_db_session.commit.side_effect = Exception("DB Commit Error")

        assert handle_session_timeout(now,session) is True
        mock_db_session.rollback.assert_called_once()
        mock_logging.exception.assert_called_once()
        assert 'last_active' not in session

@patch('fit_mafia.app_controller.db.session')
def test_create_db_session_success(mock_db_session):
    username = 'test_user'
    session_id = create_db_session(username)
    
    assert session_id is not None
    mock_db_session.add.assert_called_once()
    # The object passed to add is a Session object
    added_object = mock_db_session.add.call_args[0][0]
    assert isinstance(added_object, Session)
    assert added_object.user_name == username
    mock_db_session.commit.assert_called_once()

@patch('fit_mafia.app_controller.logging')
@patch('fit_mafia.app_controller.db.session')
def test_create_db_session_exception(mock_db_session, mock_logging):
    mock_db_session.add.side_effect = Exception("DB Add Error")
    
    session_id = create_db_session('test_user')
    
    assert session_id is None
    mock_db_session.rollback.assert_called_once()
    mock_logging.exception.assert_called_once()


# --- DELETE MEMBER TESTS ---

@patch('fit_mafia.app_controller.db.session')
def test_delete_member_success(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mobile_number = '1234567890'

        mock_member = MagicMock(spec=Member)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_member

        result = delete_member(mock_session, mobile_number)

        assert result['status'] == 'success'
        assert result['code'] == 200
        mock_db_session.delete.assert_called_once_with(mock_member)
        mock_db_session.commit.assert_called_once()


def test_delete_member_unauthorized():
    with app.test_request_context():
        mock_session = {'role': 'member'}
        result = delete_member(mock_session, '1234567890')

        assert result['status'] == 'error'
        assert result['code'] == 403
        assert result['message'] == 'Unauthorized'


def test_delete_member_missing_mobile():
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        result = delete_member(mock_session, '')

        assert result['status'] == 'error'
        assert result['code'] == 400


@patch('fit_mafia.app_controller.db.session')
def test_delete_member_not_found(mock_db_session):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mobile_number = '1234567890'

        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = None

        result = delete_member(mock_session, mobile_number)

        assert result['status'] == 'failure'
        assert result['code'] == 404
        assert result['message'] == MEMBER_NOT_FOUND


@patch('fit_mafia.app_controller.logging')
@patch('fit_mafia.app_controller.db.session')
def test_delete_member_exception(mock_db_session, mock_logging):
    with app.test_request_context():
        mock_session = {'role': 'admin'}
        mobile_number = '1234567890'

        mock_member = MagicMock(spec=Member)
        mock_query = mock_db_session.query.return_value
        mock_filter = mock_query.filter_by.return_value
        mock_filter.first.return_value = mock_member
        mock_db_session.commit.side_effect = Exception("DB Delete Error")

        result = delete_member(mock_session, mobile_number)

        assert result['status'] == 'error'
        assert result['code'] == 500
        assert result['message'] == INTERNAL_SERVER_ERROR
        mock_db_session.rollback.assert_called_once()
        mock_logging.exception.assert_called_once()

