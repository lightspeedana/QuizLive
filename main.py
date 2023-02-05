from flask import Blueprint, render_template, redirect, url_for, request, flash, Flask
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Deck, Question, Friend, Result
from flask_login import login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, rooms, send, emit, join_room, leave_room
from . import db, socketio
import random
import datetime

# I used Blueprinting here in order to make different modules of my program easily accessible from my pages. Any modules pertaining to authentication are under this auth blueprint, and all others come under the main blueprint.
main = Blueprint('main', __name__)
LFG_RANDOM = {} # These dictionaries are used with websockets and are populated as multiple users create different rooms at the same time. RANDOM is for random opponents
LFG_FRIENDS = {} # FRIENDS is for friendly opponents added via link
ROOMS = [] # This stores all the existing rooms.

"""
This section is a class to track games. It contains an ID, the ID of the deck currently playing, etc

This is used by various other methods to get the users playing, their ratings, their scores, their times per challenge, etc
"""
class room():
    def __init__(self, roomID, deckID):
        self.roomID = roomID
        self.deckID = deckID
        self.questions = list(Deck.query.filter_by(id=deckID).all()[0].questions)
        # This section chooses up to 5 random questions, based on the number of questions. They are also in a random order.
        random.shuffle(self.questions)
        if len(self.questions) > 5:
            self.questions = self.questions[:5]
        #
        # This is a group of dicts and arrays to track everything to do with the users
        self.users = []
        self.usersids = []
        self.usertimes = {}
        self.userscores = {}
        self.userqcounts = {}
        self.usercorrects = {}

""" This function just checks whether a room is finished.
It makes sure there are two users participating, and they have finished all of the questions.
The inplace or operator is used to set `notfinished` to true if any of the users have not finished all questions
"""
def getroomfinished(room):
    notfinished = False
    qcount = len(room.questions)
    if len(room.userqcounts) == 2:
        for key in room.userqcounts.keys():
            notfinished |= (room.userqcounts[key] != qcount)
    else:
        return False
    return not notfinished

""" This is a websocket listener for "query_room_finished"
This is called when the client JS wants to check whether the room is finished - used on the results screen.
"""
@socketio.on("query_room_finished")
def query_finished(data):
    room = ROOMS[data["roomID"]]
    if getroomfinished(room):
        emit("refresh")

""" This is a websocket listener for "find_game"
This handles matchmaking, or generating a room useful for sending a challenge link to another player.

The global LFG_RANDOM dictionary is used to keep track of players looking to play a specific deck.
The keys in this dict are deck IDs, and are present when there is a player looking to play that deck.
Should another player request a game for that deck, a room is created and both players are alerted about a room.
"""
@socketio.on("find_game")
def find_game(data):
    deckID = data["deckID"]
    if data["random"]:
        # dict.get here is used to check whether deckID exists in the keys for the random LFG dict
        if LFG_RANDOM.get(deckID,False):
            opponent = LFG_RANDOM[deckID]
            room_id = len(ROOMS)
            room_obj = room(room_id, deckID) # create room

            join_room(room_id)
            join_room(room_id,sid=opponent[0]) # This section lets socket send events to both players at once. SocketIO uses "rooms" to group sessions together.

            room_obj.users.append(current_user.name)
            room_obj.users.append(opponent[1])
            room_obj.usersids.append(request.sid)
            room_obj.usersids.append(opponent[0]) # This section lets the room object track the usernames and socket IDs of the players, for later reference

            ROOMS.append(room_obj) # Keep global reference of the room object
            LFG_RANDOM.pop(deckID) # Remove the request for the deck matchmaking
            emit("found_room",{"roomID":room_id}, to=room_id) # Send found room notification to both players, prompting moving to play page.

        else: # If first to request the pack, then add to the LFG dict and inform the user that they are waiting for a match
            LFG_RANDOM[deckID] = [request.sid, data["username"]]
            emit("waiting")
    
    else: # In the case of friend matchmaking...
        room_id = len(ROOMS)
        room_obj = room(room_id, deckID) # Make a new room
        ROOMS.append(room_obj)

        emit("got_room", {"roomID":room_id}) # Tell that user that a room has been created for them


""" This is a websocket listener that listens for "begin_timing"
The client calls this socket event in order to inform the server that they have begun answering the first question
such that the server can keep timing of the first question as well as subsequent questions.
"""
@socketio.on("begin_timing")
def begin_timing(data):
    roomID = int(data["url"]["pathname"].split("/")[2]) # This gets the room ID from the URL, as doing this server-side is easier than client-side

    ROOMS[roomID].usertimes[current_user.name] = [datetime.datetime.now()]
    ROOMS[roomID].userqcounts[current_user.name] = 0
    ROOMS[roomID].usercorrects[current_user.name] = 0 # Initialise room variables for current user to track corrects, answers, and times

""" This is a websocket listener for "submit_answer"
As the name implies, this listener handles the client answering a question.
"""
@socketio.on("submit_answer")
def handle_answer(data):
    roomID = int(data["url"]["pathname"].split("/")[2]) # This gets the room ID url
    room = ROOMS[roomID] # Get room object from globals

    qid = int(data["questionID"]) # Get the question ID from the socket event
    q = room.questions[qid] # Get the corresponding question

    time = datetime.datetime.now()
    delta = time - room.usertimes[current_user.name][-1]
    score = max((10 - delta.seconds) * 100, 0) # Calculate the score by calculating the seconds since the last answer was submitted, or the game was started.

    room.userqcounts[current_user.name] += 1 # Acknowledge the user completing a question
    if type(room.userscores.get(current_user.name, "")) == str: # Type == str is needed because 0 evaluates to false.
        room.userscores[current_user.name] = 0 # Initialise dict value if needed

    if int(data["answerID"]) == int(q.correct) and score > 0: # if the answer was correct, update score and correct count accordingly
        room.userscores[current_user.name] += score
        room.usercorrects[current_user.name] += 1

    qid += 1
    if qid == len(room.questions):
        emit("end_quiz", {"roomID":roomID}) # If the quiz is over, inform the user that they have finished
    else:
        nextq = room.questions[qid] # Iterates through questions
        emit("submit_question", {
            "question_ID":qid,
            "question":nextq.question,
            "a0":nextq.answer1,
            "a1":nextq.answer2,
            "a2":nextq.answer3,
            "a3":nextq.answer4,
            "score":room.userscores[current_user.name]
        }) # If the quiz is not over, send the user the next question.

""" This is a websocket handler for "join_room"
As the name implies, this is called when a player joins a room.
This is only used when challenging another player via a link.
"""
@socketio.on("join_room")
def join_room_sock(data):
    roomID = int(data["url"]["pathname"].split("/")[2]) # Similar code as above used for getting the room ID from the URL
    room_obj = ROOMS[roomID]

    join_room(roomID) # Join the socket room

    ROOMS[roomID].users.append(current_user.name) # Add user to room object attributes where necessary
    ROOMS[roomID].usersids.append(request.sid)

# Route handler for displaying another user's profile page.
@main.route('/user/<int:id>') # This allows a user's profile to be referred to via their user ID. e.g. the first user in the DB would be at /user/1
@login_required # this decorator is used throughout this file - it checks to see whether a user is logged in or not.
def userreturn(id):
    chosen_user = User.query.get_or_404(id) # if the user doesn't exist, 404, else get all their credentials
    return render_template('user.html', user=chosen_user) 

# Route handler for challenge page.
@main.route("/challenge/<int:roomID>") # Similar syntax to above, allowing you to refer to a created room via its id
def challenge(roomID):
    return render_template("challenge.html", request=request, roomID=roomID)

# Route handler for joining a game, proxy for play.html but provides template with info that the user is joining via a challenge
@main.route("/join/<int:roomID>")
def join_room_get(roomID):
    return redirect(url_for('main.play',roomID=roomID, joining="friend"))

@main.route('/') # Route for the homepage. Simply renders the home screen
def index():
    return render_template('index.html')

@main.route('/profile') # Route for the profile page.
@login_required
def profile():
    friends = Friend.query.filter_by(uid=current_user.id).all() # queries for all the friends associated with the current user's UID
    friendlist = []
    for friend in friends:
        friendlist.append(User.query.filter_by(friendid=friend.friendid).first()) # Creates a list of all user objects that are designated by having friend IDs that are linked to the user in the Friend table
    return render_template('profile.html', name=current_user.name, elo=current_user.elo, friendID=current_user.friendid, friends=friendlist)

@main.route('/profile', methods=['POST']) # The only POST request occurring on this page is adding a friend.
def profile_post():
    friendid = request.form.get('friendid') # gets friend ID parameter from form
    user = User.query.filter_by(friendid=friendid).first()
    if current_user.friendid == friendid: # prevents user from adding themselves as a friend
        flash('Unfortunately, as lonely as you may be, you cannot add yourself as a friend. :(') # A slightly mean error message
        return redirect(url_for('main.profile'))
    elif user: 
        new_friend = Friend(friendid=friendid, uid=current_user.id) # instantiates a new friend in the Friend table
        db.session.add(new_friend)
        db.session.commit()
        return redirect(url_for('main.profile'))
    else: # this means the friend ID does not exist
        flash('A user with this friend ID doesn\'t exist. Try again and check your spelling.')
        return redirect(url_for('main.profile'))

@main.route('/browse') # Allows user to browse decks.
@login_required
def browse():
    return render_template('browse.html', query=Deck.query.all()) # This query returns all decks in the entire database and displays them on this screen

@main.route('/decks/<int:id>') # Route handler for an existing deck
@login_required
def decks(id):
    chosen_deck = Deck.query.get_or_404(id) # 404s if deck doesn't exist
    questions = Question.query.filter_by(deck_id=id).all() # Displays all questions associated with the deck
    return render_template('deck.html', chosen_deck=chosen_deck, questions = questions, id=current_user.id)

@main.route('/decks/<int:id>/delete') # Allows user to delete a deck
@login_required
def delete_deck(id):
    deck = Deck.query.get_or_404(id) # checks if the deck exists
    if current_user.id == deck.uid: # checks if the user has permission to delete this deck i.e. owns it
        db.session.delete(deck)
        db.session.commit()
        return redirect(url_for('.browse')) # redirects to the deck browsing page with deleted deck now gone
    else:
        flash('You do not have permission to delete this deck.') # Flashes a message to the user saying they don't have deletion perms
        return redirect(url_for('.browse'))


@main.route('/decks/<int:deckid>/delete-question/<int:qID>') # Allows user to delete a singular question from a deck
@login_required
def delete_question(deckid, qID):
    deck = Deck.query.get_or_404(deckid) # checks if deck exists
    question = Question.query.get_or_404(qID) # checks if question in deck exists
    if current_user.id == deck.uid: # checks if the user trying to delete is the same as the creator of the deck
        db.session.delete(question)
        db.session.commit()
        return redirect(url_for('.decks', id=deckid)) # redirects the user to the deck's page with the question now gone
    else:
        flash('You do not have permission to delete this question.') # Flashes a message to say the user trying to delete the question doesn't own the deck and hence doesn't have deletion perms
        return redirect(url_for('.decks', id=deckid)) # redirects to the deck page which displays the flashed message

@main.route('/make') # Route for creating a deck
@login_required
def make():
    return render_template('make.html', name=current_user.name)

@main.route('/make', methods=['POST']) # creates a new deck
def make_post():
    title = request.form.get('title') 
    title = title.replace(" ", "_") # The application errors if deck names have spaces. This acts as input sanitisation
    new_deck = Deck(name=title, creator=current_user.name, uid=current_user.id) # uses current user's credentials to instantiate a deck with their details
    db.session.add(new_deck) 
    db.session.commit() 

    return redirect(url_for('main.browse'))

# Web route for results page post-quiz.
@main.route('/results/<int:roomID>') 
@login_required
def results(roomID):

    room = ROOMS[roomID]
    qcount = len(room.questions)
    finished = getroomfinished(room) # Get room object and whether the game has finished or not

    score = room.userscores[current_user.name] # Get user score

    if not finished: # If waiting, render the waiting page, which includes a listener to auto-refresh when the other user finishes.
        return render_template('waiting.html', score=score, roomID=roomID)

    else: # Once the game has finished (i.e both players are done)
        recorded = Result.query.filter_by(roomid=roomID).all() # Check whether there's an entry in the db for this game already

        oppscore = set(room.userscores.keys()) - {current_user.name}
        oppcorrects = room.usercorrects[list(oppscore)[0]]
        oppscore = room.userscores[list(oppscore)[0]] # Work out how the opponent did

        corrects = room.usercorrects[current_user.name] # Fetch user's successful answers

        win = score == max(score, oppscore)
        draw = win and (score == min(score, oppscore)) # Calculate win condition and check for draws

        if not recorded: # IF THE GAME RESULT HAS NOT BEEN RECORDED YET
            users = []
            scores = []
            for user in room.users:
                user_obj = User.query.filter_by(name=user).first()
                users.append(user_obj)
                score = room.userscores[user]
                scores.append(score) ### This block gets some data for each of the users; their database object and their scores.

            for user in enumerate(users): # For each user (tracking index too)
                user[1].elo *= user[1].matchcount
                user[1].elo += users[1-user[0]].elo # Rolling ELO algorithm (average of +/-400 or 0 for every game played)

                score = scores[user[0]]
                if score == max(room.userscores.values()) and not score == min(room.userscores.values()): # Check win condition
                    user[1].wincount += 1
                    user[1].elo += 400
                elif score == min(room.userscores.values()): # Check loss condition, mutually exlusive with win
                    user[1].elo -= 400

                user[1].matchcount += 1
                user[1].elo /= user[1].matchcount # Increment matchcount and finalise ELO calculation

            res = Result(roomid=roomID, user1=users[0].id, user2=users[1].id, score1=scores[0], score2=scores[1]) # Store game result in database
            db.session.add(res)
            db.session.commit()

        # Render the results page, displaying various statistics   
        return render_template('results.html',winner=win, draw=draw, score=score, oppscore=oppscore, elo=current_user.elo, total=qcount, correct=corrects, oppcorrect=oppcorrects)

# Route handler for /play/
# Render the play page, starting with the game's first question
@main.route('/play/<int:roomID>/<joining>')
@main.route('/play/<int:roomID>')
@login_required
def play(roomID, joining=False):
    room = ROOMS[roomID]
    firstq = room.questions[0]
    return render_template('play.html', joining=joining, firstq=firstq) 

@main.route('/add') # This screen allows you to add a question to any deck that the user owns
@login_required
def add():
    decklist = Deck.query.filter_by(uid=current_user.id).all() # Querying for all decks associated with the current user's ID.
    return render_template('add.html', edit=False, decklist=decklist)

@main.route('/add', methods=['POST']) # This allows for the form regarding adding/editing questions to be posted to the server.
def add_question():
    
    edit = False # defaults to False as we presume the question is not being edited. This is a boolean value.
    if request.form.get("edit"):
        edit = int(request.form.get("edit")) # Check whether the question is being edited or not

    question = request.form.get('question')
    question1 = request.form.get('question1')
    question2 = request.form.get('question2')
    question3 = request.form.get('question3')
    question4 = request.form.get('question4')
    correct = request.form["correct"]
    deck_name = request.form.get('deckselect')
    deck_id = Deck.query.filter_by(name=deck_name).first()
    if not edit: # If the question isn't being edited, then a new question object can be instantiated
        new_question = Question(question=question, answer1=question1, answer2=question2, answer3=question3, answer4=question4, correct=correct, deck_id=deck_id.id)
        db.session.add(new_question)
    else:
        ### THIS SECTION ACCOUNTS FOR WHEN EDITING THE QUESTION, NOT CREATING A NEW ONE
        edit = edit - 1
        question_obj = Question.query.filter_by(id=edit).first() 
        question_obj.question = question
        question_obj.answer1 = question1
        question_obj.answer2 = question2
        question_obj.answer3 = question3
        question_obj.answer4 = question4
        question_obj.correct = correct
        question_obj.deck_id = deck_id.id

    db.session.commit()

    return redirect(url_for('main.browse')) # returns to deck browsing screen

# Edit route for the questions, largely just the add page but with the values filled in already.
@main.route("/decks/<int:deckID>/edit-question/<int:qID>")
@login_required
def edit_question(deckID, qID):
    decklist = Deck.query.filter_by(uid=current_user.id).all()
    deck = Deck.query.get_or_404(deckID) # checking if IDs exist 
    question = Question.query.get_or_404(qID)
    return render_template('add.html', edit=True, decklist=decklist, selecteddeck=deck, question=question)

@main.route('/select') # deck selection screen for playing a match.
@login_required
def select():
    decklist = Deck.query.all() # queries for all existing decks and returns them to the dropdown.
    return render_template('select.html', decklist=decklist, user=current_user)

if __name__ == '__main__': # runs socket.io so that websockets can be opened across the application.
    socketio.run(main,debug=True)