from flask import Flask
import os
from datetime import timedelta
import config

from fit_mafia.app import app as fit_mafia_blueprint
from health_check import app as health_blueprint
from swagger import configure_swagger

main_app = Flask(__name__) # NOSONAR

main_app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
main_app.permanent_session_lifetime = timedelta(minutes=30)

swagger=configure_swagger(main_app)
swagger.register_blueprint(fit_mafia_blueprint)
swagger.register_blueprint(health_blueprint)

if __name__ == "__main__":
    main_app.run(host='127.0.0.1', port=5000)
    