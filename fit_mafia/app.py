import datetime
import os

from flask import flash, redirect, render_template, request, session, url_for, jsonify
from flask_smorest import Blueprint

from fit_mafia import app_controller
from fit_mafia.constants import HOME_PAGE, PUBLIC_PAGE, LOGIN_PAGE, PUBLIC_TEMPLATE, RECEIPT_TEMPLATE
from fit_mafia.schemas import MemberSchema,LoginRequestSchema

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.join(os.path.dirname(__file__), "static")


app = Blueprint('fit_mafia', __name__,
                template_folder=template_dir,
                static_folder=static_dir,
                static_url_path="/fit_mafia/static",
                description="Operations for the Fit Mafia application")

@app.before_request
def require_auth():
    """Check authentication before every request in this Blueprint except public endpoints."""
    # Guard clause: Only run auth logic for requests that belong to the 'fit_mafia' blueprint.
    if not request.endpoint or not request.endpoint.startswith('fit_mafia.'):
        return

    public_endpoints = [PUBLIC_PAGE, LOGIN_PAGE]

    if request.endpoint in public_endpoints or request.endpoint == 'fit_mafia.static':
        return None

    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for(PUBLIC_PAGE))

    now = datetime.datetime.now()
    if app_controller.handle_session_timeout(now,session):
        return redirect(url_for(PUBLIC_PAGE))

    session.permanent = True
    if 'session_id' not in session:
        app_controller.create_db_session(session.get('username', 'Admin'))

    session['last_active'] = now.isoformat()
    return None

@app.route('/', methods=['GET'])
def public_page():
    """Renders the public-facing page, or redirects to home if logged in."""
    if session.get('logged_in'):
        return redirect(url_for(HOME_PAGE))
    return render_template(PUBLIC_TEMPLATE)


@app.route('/home', methods=['GET'])
def home():
    response=app_controller.home(session)
    if response['status']=='success':
        template_data=response['template_data']
        return render_template('home.html', **template_data)
    else:
        flash(response['message'], "error")
        return render_template(PUBLIC_TEMPLATE, error=response['message'])

@app.route('/logout', methods=['GET'])
def logout():
    app_controller.logout(session)
    flash("You have been logged out.", "info")
    return redirect(url_for(PUBLIC_PAGE))


@app.route('/print_receipt/<transaction_id>', methods=['GET'])
def print_receipt(transaction_id):
    response=app_controller.print_receipt(transaction_id,session)
    if response['status']=='success':
        return render_template(RECEIPT_TEMPLATE, **response['template_data'])
    else:
        return redirect(url_for(HOME_PAGE))


@app.route('/api/member/<mobile_number>', methods=['GET'])
@app.response(200, MemberSchema)
def get_member(mobile_number):
    response=app_controller.get_member(mobile_number,session)
    if response['status']=='success':
        return response['message']
    else:
        return jsonify({response['status']: response['message']}), response['code']


@app.route('/login', methods=['POST'])
@app.arguments(LoginRequestSchema, location="form")
def login(args):
    """User Login"""
    try:
        username = args["username"]
        password = args["password"]
        response = app_controller.login(username, password)
        
        if response['status'] == 'success':
            session.update(response['session_data'])
            flash("Logged in successfully!", "success")
            return redirect(url_for(HOME_PAGE))
        else:
            flash(response['message'], "error")
            return render_template(PUBLIC_TEMPLATE, error=response['message'])
    except Exception as e:
        print (e)

@app.route('/register_transaction', methods=['POST'])
def register_transaction():
    response=app_controller.register_transaction(session,request.form.to_dict())
    if response['status']=="success":
        return redirect(url_for(HOME_PAGE))
    else:
        flash(response['message'], "error")
        return redirect(url_for(HOME_PAGE))

@app.route('/register_member', methods=['POST'])
def register_member():
    response = app_controller.register_member(session, request.form.to_dict(), request.files.get('photo'))
    return jsonify({'status': response['status'], 'message': response['message']}), 200

@app.route('/update_member', methods=['POST'])
def update_member():
    response = app_controller.update_member(session, request.form.to_dict(), request.files.get('photo'))
    return jsonify({'status': response['status'], 'message': response['message']}), 200

@app.route('/update_vitals', methods=['POST'])
def update_vitals():
    response=app_controller.update_vitals(session, request.form.to_dict())
    return jsonify({response['status']: response['message']}), response['code']

@app.route('/renew_subscription', methods=['POST'])
def renew_subscription():
    response=app_controller.renew_subscription(session,request.form.to_dict())
    return jsonify({response['status']: response['message']}), response['code']

@app.route('/delete_member', methods=['POST'])
@app.route('/delete_member/<mobile_number>', methods=['POST', 'DELETE'])
def delete_member(mobile_number=None):
    if not mobile_number:
        data = request.get_json(silent=True) or request.form.to_dict()
        mobile_number = data.get('mobile_number')
    response = app_controller.delete_member(session, mobile_number)
    return jsonify({'status': response['status'], 'message': response['message']}), response.get('code', 200)

