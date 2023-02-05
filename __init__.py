from flask import Flask, render_template
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

# This initialises SQLAlchemy for use with databases and querying.
db = SQLAlchemy()
socketio = SocketIO()

def page_not_found(e): # If a page doesn't exist on the server, then this handles the error. 
  return render_template('404.html'), 404

def create_app():
    app = Flask(__name__) # This instantiates the flask app and server
    app.register_error_handler(404, page_not_found) # This registers the above error handling code 

    app.config['SECRET_KEY'] = 'de0baae8808bb178caaeb3b06082374c7f1c4d62489c8506' # a very long secret key. This is generated and used to hash passwords and session cookies. I made it long for maximum security
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite' # connects the server to the sqlite database in the root folder.
    
    db.init_app(app) # initialises the database for the server
    socketio.init_app(app) # initialises websockets for the actual game
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login' # designates the login manager as the auth.login route.
    login_manager.init_app(app)

    from .models import User # imports the User object from models so it can be handled and queried below

    @login_manager.user_loader # loads a user via this decorator
    def load_user(user_id):
        # When a user is instantiated or loaded in via login, this queries the database via their ID and allows
        return User.query.get(int(user_id))
    
    from .auth import auth as auth_blueprint # imports blueprints from auth 
    app.register_blueprint(auth_blueprint)
    from .main import main as main_blueprint # imports blueprints from main 
    app.register_blueprint(main_blueprint)
    return app