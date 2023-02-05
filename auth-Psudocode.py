from flask import Blueprint, render_template, redirect, url_for, request, flash
                                                            ENDFOR
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User
from flask_login import login_user, logout_user, login_required, current_user
from . import db
import random
import string
import re
# I used Blueprinting here in order to make different modules of my program easily accessible from my pages. Any modules pertaining to authentication are under this auth blueprint, AND all others come under the main blueprint.
                                             ENDIF
auth <- Blueprint('auth', __name__)
@auth.route('/login')
FUNCTION login():
    try:
        IF current_user.id != None:
            RETURN render_template('return.html')
        ELSE:
            RETURN render_template('login.html')
        ENDIF
    except:
        RETURN render_template('login.html')
ENDFUNCTION

@auth.route('/login', methods=['POST'])
FUNCTION login_post():
    email <- request.form.get('email')
                    ENDFOR
    password <- request.form.get('password')
                       ENDFOR
    remember <- True IF request.form.get('remember') else False
                    ENDIF
                               ENDFOR
    user <- User.query.filter_by(email=email).first()
    # check IF the user actually exists
            ENDIF
    # take the user-supplied password, hash it, AND compare it to the hashed password in the database
    IF not user OR not check_password_hash(user.password, password):
        flash('Please check your login details AND try again.')
        RETURN redirect(url_for('auth.login')) # IF the user doesn't exist or password is wrong, reload the page
                                                 ENDIF
                            ENDFOR
    # IF the above check passes, then we know the user has the right credentials
    ENDIF
      ENDIF
    login_user(user, remember=remember)
    RETURN redirect(url_for('main.profile'))
ENDFUNCTION

                        ENDFOR
@auth.route('/signup')
FUNCTION signup():
    try:
        IF current_user.id != None:
            RETURN render_template('return.html')
        ELSE:
            RETURN render_template('signup.html')
        ENDIF
    except:
        RETURN render_template('signup.html')
ENDFUNCTION

@auth.route('/signup', methods=['POST'])
FUNCTION signup_post():
    email <- request.form.get('email')
                    ENDFOR
    name <- request.form.get('name')
                   ENDFOR
    password <- request.form.get('password')
                       ENDFOR
    user <- User.query.filter_by(email=email).first()
    length_error <- len(password) < 8
    digit_error <- re.search(r"\d", password) is None
    uppercase_error <- re.search(r"[A-Z]", password) is None
    symbol_error <- re.search(r"[ !#$%&'()*+,-./[\\\]^_`{|}~"+r'"]', password) is None
    password_ok <- not ( length_error or digit_error or uppercase_error or symbol_error )
    IF not password_ok:
        flash('Password does not meet the complexity requirements. Please ensure it contains an uppercase letter, number AND symbol AND is at least 8 characters in length.')
        RETURN redirect(url_for('auth.signup'))
    ENDIF
                            ENDFOR
    IF user:
        flash('Email address already exists. Please go to the Login page.')
        RETURN redirect(url_for('auth.signup'))
    ENDIF
                            ENDFOR
    friendID <- ''.join((random.choice(string.ascii_letters + string.digits) for i in range(10)))
                                                                            ENDFOR
    new_user <- User(email=email, name=name, password=generate_password_hash(password, method='sha256'), friendid=friendID, elo=1000, wincount=0, matchcount=0)
    db.session.add(new_user)
    db.session.commit()
    RETURN redirect(url_for('auth.login'))
ENDFUNCTION

                        ENDFOR
@auth.route('/logout')
@login_required
FUNCTION logout():
    logout_user()
    RETURN redirect(url_for('main.index')
