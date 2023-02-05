from flask_login import UserMixin
from . import db
from datetime import datetime

'''
The User class models any user added to the system. Each line specifies a column in the Users table, and the appropriate data type.
'''
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    __table_args__ = {'extend_existing': True} # This means that if the database is reinitialised, existing records will be extended and not replaced. I set this to True across this file to avoid completely removing testing credentials.
    id = db.Column(db.Integer, primary_key=True) # All SQLite tables must possess primary keys.
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    friendid = db.Column(db.String(10))
    elo = db.Column(db.Integer)
    friends = db.relationship('Friend', backref='user', lazy='dynamic') # This models a relationship to the Friend table, allowing each user to have multiple friends associated with their profile.
    wincount = db.Column(db.Integer, default=0)
    matchcount = db.Column(db.Integer, default=0)

'''
The Deck class models any set of quiz questions.
'''
class Deck(db.Model):
    __tablename__ = 'decks'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True)
    creation_time = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    creator = db.Column(db.String(1000))
    uid = db.Column(db.Integer)
    questions = db.relationship('Question', backref='deck', lazy='dynamic') # This models a one to many relationship to the Question table.
    def __repr__(self):
        return '<Deck: %r>' % self.name

'''
The Friend class models friends which a user possesses on their friends list. This is directly linked to the users table.
'''
class Friend(db.Model):
    __tablename__ = 'friends'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    friendid = db.Column(db.String(10))
    uid = db.Column(db.Integer, db.ForeignKey('users.id')) # Foreign key to a user, allowing each user to "possess" the friend designated by their friend ID.

'''
The Question class models a singular question, with appropriate answers and a link back to its corresponding deck via a foreign key.
'''
class Question(db.Model):
    __tablename__ = 'questions'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text)
    answer1 = db.Column(db.Text)
    answer2 = db.Column(db.Text)
    answer3 = db.Column(db.Text)
    answer4 = db.Column(db.Text)
    correct = db.Column(db.Text) # This contains the value of the Radio button clicked when creating a question.
    deck_id = db.Column(db.Integer, db.ForeignKey('decks.id'))

'''
The Result class models the results of a quiz match. The users associated with each match are stored in it, along with their final scores. 
'''
class Result(db.Model):
    __tablename__ = 'results'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    roomid = db.Column(db.Integer)
    user1 = db.Column(db.Integer, db.ForeignKey("users.id"))
    user2 = db.Column(db.Integer, db.ForeignKey("users.id"))
    score1 = db.Column(db.Integer)
    score2 = db.Column(db.Integer)

def init_db(): # This function allows me to quickly initialise the database through a Python REPL.
    db.create_all()

if __name__ == '__main__':
    init_db()