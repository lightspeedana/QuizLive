from flask import Blueprint, render_template, redirect, url_for, request, flash, Flask
                                                            ENDFOR
from werkzeug.security import generate_password_hash, check_password_hash
from .models import User, Deck, Question, Friend, Result
from flask_login import login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, rooms, send, emit, join_room, leave_room
from . import db, socketio
import random
import datetime
main <- Blueprint('main', __name__)
LFG_RANDOM <- {}
LFG_FRIENDS <- {}
ROOMS <- []
CLASS room():
    FUNCTION __init__(self, roomID, deckID):
         roomID <- roomID
         deckID <- deckID
         questions <- list(Deck.query.filter_by(id=deckID).all()[0].questions)
        random.shuffle( questions)
        IF len( questions) > 5:
             questions <-  questions[:5]
        ENDIF
         users <- []
         usersids <- []
         usertimes <- {}
         userscores <- {}
         userqcounts <- {}
         usercorrects <- {}
    ENDFUNCTION

ENDCLASS

FUNCTION getroomfinished(room):
    notfinished <- False
    qcount <- len(room.questions)
    IF len(room.userqcounts) = 2:
        for key in room.userqcounts.keys():
            notfinished |= (room.userqcounts[key] != qcount)
        ENDFOR
    ELSE:
        RETURN False
    ENDIF
    RETURN not notfinished
ENDFUNCTION

@socketio.on("query_room_finished")
FUNCTION query_finished(data):
    room <- ROOMS[data["roomID"]]
    IF getroomfinished(room):
        emit("refresh")
    ENDIF
ENDFUNCTION

@socketio.on("find_game")
FUNCTION find_game(data):
    deckID <- data["deckID"]
    IF data["random"]:
        IF LFG_RANDOM.get(deckID,False):
            opponent <- LFG_RANDOM[deckID]
            room_id <- len(ROOMS)
            room_obj <- room(room_id, deckID)
            join_room(room_id)
            join_room(room_id,sid=opponent[0])
            room_obj.users.append(current_user.name)
            room_obj.users.append(opponent[1])
            room_obj.usersids.append(request.sid)
            room_obj.usersids.append(opponent[0])
            ROOMS.append(room_obj)
            LFG_RANDOM.pop(deckID)
            emit("found_room",{"roomID":room_id}, to=room_id)
        ELSE:
            LFG_RANDOM[deckID] <- [request.sid, data["username"]]
            emit("waiting")
        ENDIF
    ELSE:
        room_id <- len(ROOMS)
        room_obj <- room(room_id, deckID)
        #join_room(room_id)
        #room_obj.users.append(current_user.name)
        #room_obj.usersids.append(request.sid)
        ROOMS.append(room_obj)
        emit("got_room", {"roomID":room_id})
    ENDIF
ENDFUNCTION

@socketio.on("begin_timing")
FUNCTION begin_timing(data):
    roomID <- int(data["url"]["pathname"].split("/")[2])
    ROOMS[roomID].usertimes[current_user.name] <- [datetime.datetime.now()]
    ROOMS[roomID].userqcounts[current_user.name] <- 0
    ROOMS[roomID].usercorrects[current_user.name] <- 0
    OUTPUT "BEGUN_TIMING"
    for i in dir(ROOMS[roomID]):
        OUTPUT i, getattr(ROOMS[roomID], i)
ENDFUNCTION

    ENDFOR
@socketio.on("submit_answer")
FUNCTION handle_answer(data):
    roomID <- int(data["url"]["pathname"].split("/")[2])
    room <- ROOMS[roomID]
    qid <- int(data["questionID"])
    q <- room.questions[qid]
    time <- datetime.datetime.now()
    delta <- time - room.usertimes[current_user.name][-1]
    score <- max((10 - delta.seconds) * 100, 0)
    room.userqcounts[current_user.name] += 1
    IF type(room.userscores.get(current_user.name, "")) = str:
        room.userscores[current_user.name] <- 0
    ENDIF
    IF int(data["answerID"]) = int(q.correct) AND score > 0:
        room.userscores[current_user.name] += score
        room.usercorrects[current_user.name] += 1
    ENDIF
    qid += 1
    IF qid = len(room.questions):
        emit("end_quiz", {"roomID":roomID})
    ELSE:
        nextq <- room.questions[qid]
        emit("submit_question", {
            "question_ID":qid,
            "question":nextq.question,
            "a0":nextq.answer1,
            "a1":nextq.answer2,
            "a2":nextq.answer3,
            "a3":nextq.answer4,
            "score":room.userscores[current_user.name]
        })
    ENDIF
ENDFUNCTION

@socketio.on("join_room")
FUNCTION join_room_sock(data):
    roomID <- int(data["url"]["pathname"].split("/")[2])
    room_obj <- ROOMS[roomID]
    join_room(roomID)
    ROOMS[roomID].users.append(current_user.name)
    ROOMS[roomID].usersids.append(request.sid)
ENDFUNCTION

@main.route('/user/<int:id>')
@login_required
FUNCTION userreturn(id):
    chosen_user <- User.query.get_or_404(id)
    RETURN render_template('user.html', user=chosen_user)
ENDFUNCTION

@main.route("/challenge/<int:roomID>")
FUNCTION challenge(roomID):
    RETURN render_template("challenge.html", request=request, roomID=roomID)
ENDFUNCTION

@main.route("/join/<int:roomID>")
FUNCTION join_room_get(roomID):
    RETURN redirect(url_for('main.play',roomID=roomID, joining="friend"))
ENDFUNCTION

                        ENDFOR
@main.route('/')
FUNCTION index():
    RETURN render_template('index.html')
ENDFUNCTION

@main.route('/profile')
@login_required
FUNCTION profile():
    friends <- Friend.query.filter_by(uid=current_user.id).all()
    friendlist <- []
    for friend in friends:
        friendlist.append(User.query.filter_by(friendid=friend.friendid).first())
    ENDFOR
    RETURN render_template('profile.html', name=current_user.name, elo=current_user.elo, friendID=current_user.friendid, friends=friendlist)
ENDFUNCTION

@main.route('/profile', methods=['POST'])
FUNCTION profile_post():
    friendid <- request.form.get('friendid')
                       ENDFOR
    user <- User.query.filter_by(friendid=friendid).first()
    IF current_user.friendid = friendid:
        flash('Unfortunately, as lonely as you may be, you cannot add yourself as a friend. :(')
                 ENDFOR
        RETURN redirect(url_for('main.profile'))
                            ENDFOR
    ELSEIF user:
        new_friend <- Friend(friendid=friendid, uid=current_user.id)
        db.session.add(new_friend)
        db.session.commit()
        RETURN redirect(url_for('main.profile'))
                            ENDFOR
    ELSE:
        flash('A user with this friend ID doesn\'t exist. Try again AND check your spelling.')
        RETURN redirect(url_for('main.profile'))
    ENDIF
ENDFUNCTION

                            ENDFOR
@main.route('/browse')
@login_required
FUNCTION browse():
    RETURN render_template('browse.html', query=Deck.query.all())
ENDFUNCTION

@main.route('/decks/<int:id>')
@login_required
FUNCTION decks(id):
    chosen_deck <- Deck.query.get_or_404(id)
    questions <- Question.query.filter_by(deck_id=id).all()
    RETURN render_template('deck.html', chosen_deck=chosen_deck, questions = questions, id=current_user.id)
ENDFUNCTION

@main.route('/decks/<int:id>/delete')
@login_required
FUNCTION delete_deck(id):
    deck <- Deck.query.get_or_404(id)
    IF current_user.id = deck.uid:
        db.session.delete(deck)
        db.session.commit()
        RETURN redirect(url_for('.browse'))
                            ENDFOR
    ELSE:
        flash('You do not have permission to delete this deck.')
        RETURN redirect(url_for('.browse'))
    ENDIF
ENDFUNCTION

                            ENDFOR
@main.route('/decks/<int:deckid>/delete-question/<int:qID>')
@login_required
FUNCTION delete_question(deckid, qID):
    deck <- Deck.query.get_or_404(deckid)
    question <- Question.query.get_or_404(qID)
    IF current_user.id = deck.uid:
        db.session.delete(question)
        db.session.commit()
        RETURN redirect(url_for('.decks', id=deckid))
                            ENDFOR
    ELSE:
        flash('You do not have permission to delete this question.')
        RETURN redirect(url_for('.decks', id=deckid))
    ENDIF
ENDFUNCTION

                            ENDFOR
@main.route('/make')
@login_required
FUNCTION make():
    RETURN render_template('make.html', name=current_user.name)
ENDFUNCTION

@main.route('/make', methods=['POST'])
FUNCTION make_post():
    title <- request.form.get('title')
                    ENDFOR
    title <- title.replace(" ", "_")
    new_deck <- Deck(name=title, creator=current_user.name, uid=current_user.id)
    db.session.add(new_deck)
    db.session.commit()
    RETURN redirect(url_for('main.browse'))
ENDFUNCTION

                        ENDFOR
@main.route('/results/<int:roomID>')
@login_required
FUNCTION results(roomID):
    room <- ROOMS[roomID]
    qcount <- len(room.questions)
    finished <- getroomfinished(room)
    score <- room.userscores[current_user.name]
    IF not finished:
        RETURN render_template('waiting.html', score=score, roomID=roomID)
    ELSE:
        recorded <- Result.query.filter_by(roomid=roomID).all()
        oppscore <- set(room.userscores.keys()) - {current_user.name}
        oppcorrects <- room.usercorrects[list(oppscore)[0]]
        oppscore <- room.userscores[list(oppscore)[0]]
        corrects <- room.usercorrects[current_user.name]
        win <- score = max(score, oppscore)
        draw <- win AND (score = min(score, oppscore))
        IF not recorded:
            users <- []
            scores <- []
            for user in room.users:
                user_obj <- User.query.filter_by(name=user).first()
                users.append(user_obj)
                score <- room.userscores[user]
                scores.append(score)
            ENDFOR
            OUTPUT users, scores
            for user in enumerate(users):
                user[1].elo *= user[1].matchcount
                user[1].elo += users[1-user[0]].elo
                score <- scores[user[0]]
                IF score = max(room.userscores.values()) AND not score = min(room.userscores.values()):
                    user[1].wincount += 1
                    user[1].elo += 400
                ENDIF
                IF score = min(room.userscores.values()):
                    user[1].elo -= 400
                ENDIF
                user[1].matchcount += 1
                user[1].elo /= user[1].matchcount
            ENDFOR
            res <- Result(roomid=roomID, user1=users[0].id, user2=users[1].id, score1=scores[0], score2=scores[1])
            db.session.add(res)
            db.session.commit()
        ENDIF
        RETURN render_template('results.html',winner=win, draw=draw, score=score, oppscore=oppscore, elo=current_user.elo, total=qcount, correct=corrects, oppcorrect=oppcorrects)
    ENDIF
ENDFUNCTION

@main.route('/play/<int:roomID>/<joining>')
@main.route('/play/<int:roomID>')
@login_required
FUNCTION play(roomID, joining=False):
    room <- ROOMS[roomID]
    firstq <- room.questions[0]
    RETURN render_template('play.html', joining=joining, firstq=firstq)
ENDFUNCTION

@main.route('/add')
@login_required
FUNCTION add():
    decklist <- Deck.query.filter_by(uid=current_user.id).all()
    RETURN render_template('add.html', edit=False, decklist=decklist)
ENDFUNCTION

@main.route('/add', methods=['POST'])
FUNCTION add_question():
    edit <- False
    IF request.form.get("edit"):
               ENDFOR
        edit <- int(request.form.get("edit"))
    ENDIF
                           ENDFOR
    question <- request.form.get('question')
                       ENDFOR
    question1 <- request.form.get('question1')
                        ENDFOR
    question2 <- request.form.get('question2')
                        ENDFOR
    question3 <- request.form.get('question3')
                        ENDFOR
    question4 <- request.form.get('question4')
                        ENDFOR
    correct <- request.form["correct"]
                      ENDFOR
    deck_name <- request.form.get('deckselect')
                        ENDFOR
    deck_id <- Deck.query.filter_by(name=deck_name).first()
    IF not edit:
        new_question <- Question(question=question, answer1=question1, answer2=question2, answer3=question3, answer4=question4, correct=correct, deck_id=deck_id.id)
        db.session.add(new_question)
    ELSE:
        edit <- edit - 1
        question_obj <- Question.query.filter_by(id=edit).first()
        question_obj.question <- question
        question_obj.answer1 <- question1
        question_obj.answer2 <- question2
        question_obj.answer3 <- question3
        question_obj.answer4 <- question4
        question_obj.correct <- correct
        question_obj.deck_id <- deck_id.id
    ENDIF
    db.session.commit()
    RETURN redirect(url_for('main.browse'))
ENDFUNCTION

                        ENDFOR
@main.route("/decks/<int:deckID>/edit-question/<int:qID>")
@login_required
FUNCTION edit_question(deckID, qID):
    decklist <- Deck.query.filter_by(uid=current_user.id).all()
    deck <- Deck.query.get_or_404(deckID)
    question <- Question.query.get_or_404(qID)
    RETURN render_template('add.html', edit=True, decklist=decklist, selecteddeck=deck, question=question)
ENDFUNCTION

@main.route('/select')
@login_required
FUNCTION select():
    decklist <- Deck.query.all()
    RETURN render_template('select.html', decklist=decklist, user=current_user)
ENDFUNCTION

IF __name__ = '__main__':
