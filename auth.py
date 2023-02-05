from flask import Blueprint, render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from flask_login import login_user, logout_user, login_required, current_user
from . import db
import random
import string
import re

# I used Blueprinting here in order to make different modules of my program easily accessible from my pages. Any modules pertaining to authentication are under this auth blueprint, and all others come under the main blueprint.
auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    try: # Flask sometimes uses anonymous user objects. If the user doesn't have an ID it may be anonymous and this causes a 500 error. Therefore, if an error occurs, the anonymous user must be logged in
        if current_user.id != None:
            return render_template('return.html') # denies user access to this page if logged in 
        else:
            return render_template('login.html')
    except:
        return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email') # gets all details inputted into form
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False # checks if the remember me box was checked

    user = User.query.filter_by(email=email).first()
    # checks if the user exists
    # takes the password and compares its hash to the hash in the database
    if not user or not check_password_hash(user.password, password):
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login')) # reloads the page with the flashed error message if there is an error in credentials.

    # logs user in using Flask_login
    login_user(user, remember=remember) # remember attribute checks if the remember me checkbox was ticked. Stores cookie if so
    return redirect(url_for('main.profile')) # redirects them to their profile page.

@auth.route('/signup')
def signup():
    try: # see login function for reasoning behind exception handle
        if current_user.id != None:
            return render_template('return.html') # denies user access to this page if logged in
        else:
            return render_template('signup.html')
    except:
        return render_template('signup.html')

@auth.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email') # gets form details
    name = request.form.get('name')
    password = request.form.get('password')
    user = User.query.filter_by(email=email).first()
    # Complex regex listed below in order to validate a password
    length_error = len(password) < 8 # checks if password is correct length
    digit_error = re.search(r"\d", password) is None # checks if password has a number
    uppercase_error = re.search(r"[A-Z]", password) is None # checks if password has an uppercase letter
    symbol_error = re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None # checks for symbols in a password
    password_ok = not ( length_error or digit_error or uppercase_error or symbol_error ) # a password is ok if none of these checks work out
    if not password_ok: # if the password isn't ok, flash an error message
        flash('Password does not meet the complexity requirements. Please ensure it contains an uppercase letter, number and symbol and is at least 8 characters in length.')
        return redirect(url_for('auth.signup'))
    if user: # if the user with that email already exists, then error and make them login
        flash('Email address already exists. Please go to the Login page.')
        return redirect(url_for('auth.signup'))
    friendID = ''.join((random.choice(string.ascii_letters + string.digits) for i in range(10))) # create a random ten character string for the friend ID.
    new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'), friendid=friendID, elo=1000, wincount=0, matchcount=0) # hashes password for storage in database using the sha256 algorithm
    db.session.add(new_user) # instantiates new user
    db.session.commit()

    return redirect(url_for('auth.login')) # redirects to login page after successful sign up

@auth.route('/logout') # logout route
@login_required
def logout():
    logout_user() # logs out user using Flask_login
    return redirect(url_for('main.index'))