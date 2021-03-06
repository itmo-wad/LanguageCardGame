import hashlib
import random
import uuid

import sqlalchemy
from flask import Response, Flask, render_template, redirect, make_response, request, send_from_directory, jsonify
from sqlalchemy import or_, func
from waitress import serve

from decorators import authenticate
from models import User, Category, Word, Statistic, Session

app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'Wow a Secret!'


@app.route("/category", methods=["GET"])
@authenticate
def category(user, *args, **kwargs):
    """Function returns all existing categories"""
    session = Session()
    categories = []
    all_categories = session.query(Category).all()
    for category in all_categories:
        categories.append({"id": category.id, "ru_name": category.ru_name, "en_name": category.en_name,
                           "image": category.image})
    Session.remove()
    return render_template("category.html", categories=categories, user=user)


@app.route("/category/<int:category_id>", methods=["GET"])
@authenticate
def word(user, category_id, *args, **kwargs):
    """Function returns <count> words from category <category_id>"""
    session = Session()

    words = []
    all_words = []

    new_or_memorized_words = session.query(Word).join(Statistic, (Word.id == Statistic.word_id) &
                                                      (Word.category_id == category_id) & (
                                                                  Statistic.user_id == user["id"]),
                                                      isouter=True).filter(
        Word.category_id == category_id, or_(Statistic.is_memorized == None, Statistic.is_memorized == True)).all()


    forgotten_words = session.query(Word).join(Statistic, (Word.id == Statistic.word_id) &
                                               (Word.category_id == category_id) & (Statistic.user_id == user["id"]),
                                               isouter=True).filter(
        Word.category_id == category_id, or_(Statistic.is_memorized == None, Statistic.is_memorized == False)).all()

    new_or_memorized_words_count = 5
    forgotten_words_count = 5

    if len(forgotten_words) < forgotten_words_count:
        forgotten_words_count = len(forgotten_words)
        new_or_memorized_words_count = 10 - forgotten_words_count

    try:
        all_words.extend(random.sample(new_or_memorized_words, new_or_memorized_words_count))
    except ValueError:
        all_words.extend(random.sample(new_or_memorized_words, len(new_or_memorized_words)))
    try:
        all_words.extend(random.sample(forgotten_words, forgotten_words_count))
    except ValueError:
        all_words.extend(random.sample(forgotten_words, len(forgotten_words)))

    for word in all_words:
        words.append({"id": word.id, "ru_name": word.ru_name, "en_name": word.en_name})
    Session.remove()
    return render_template("game.html", words=words, user=user)


@app.route("/image/<image>", methods=["GET"])
@authenticate
def image(user, image, *args, **kwargs):
    """Function returns categories requested image"""
    if request.method == "GET":
        if image in [None, "None", "", "default"]:
            return send_from_directory('static/images', "default.jpg")
        return send_from_directory('static/images', f"{image}")


@app.route("/game", methods=["POST"])
@authenticate
def game(user, *args, **kwargs):
    """
    Function accepts user decisions during the game
    :request: {"word_id" : 1, "is_memorized" : true}
    :return:
        HTTP STATUS 201 in case word in statistic was created
        HTTP STATUS 204 in case word in statistic was modified
        HTTP STATUS 400 in case of input error
        HTTP STATUS 404 in case word <word_id> was not found
        HTTP STATUS 500 in case internal error
    """
    session = Session()
    try:
        data = request.get_json()
    except Exception:
        return Response('{"message": "???? ?????????????? ?????????????????????????????? ????????????"}', status=400, mimetype='application/json')

    word_id = data.get("word_id")
    is_memorized = data.get("is_memorized")

    if word_id is None or is_memorized is None:
        return Response('{"message": "???????????????????? ???????????????????????? ????????"}', status=400, mimetype='application/json')

    if not isinstance(word_id, int):
        return Response('{"message": "???????? word_id ???? ???????????????? ????????????"}', status=400, mimetype='application/json')
    if not isinstance(is_memorized, bool):
        return Response('{"message": "???????? word_id ???? ???????????????? ????????????"}', status=400, mimetype='application/json')

    instance = session.query(Word).where(Word.id == word_id).first()
    if not instance:
        Session.remove()
        return Response(status=404)

    instance = session.query(Statistic).where(Statistic.word_id == word_id, Statistic.user_id == user["id"])
    if instance.first():
        instance.update({'is_memorized': is_memorized})
        session.commit()
        Session.remove()
        return Response(status=204)
    else:
        try:
            instance = Statistic(user_id=user["id"], word_id=word_id, is_memorized=is_memorized)
            session.add(instance)
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            Session.remove()
            return Response(status=500)
        Session.remove()
        return Response(status=201)


@app.route("/statistic", methods=["GET"])
@authenticate
def statistic(user, *args, **kwargs):
    """Function returns statistics for current user on learned words"""
    session = Session()
    words_in_each_category = session.query(Category.id, func.count(Word.id)).join(Word, Category.id == Word.category_id,
                                                                                  isouter=True).group_by(
        Category.id).all()

    extended_statistic = session.query(Statistic, Word, Category).join(Word, Statistic.word_id == Word.id).join(
        Category,
        Word.category_id == Category.id).filter(
        Statistic.user_id == user["id"])
    memorized_words_in_each_category = {}
    for statistic, word, category in extended_statistic:
        if category.id in memorized_words_in_each_category:
            if statistic.is_memorized:
                memorized_words_in_each_category[category.id] += 1
        else:
            memorized_words_in_each_category[category.id] = 1
    statistic = []
    for category in session.query(Category).all():
        words_in_category = 0
        for words in words_in_each_category:
            if words[0] == category.id:
                words_in_category = words[1]

        try:
            memorized_words = memorized_words_in_each_category[category.id]
        except KeyError:
            memorized_words = 0
        statistic.append({
            "id": category.id,
            "ru_name": category.ru_name,
            "en_name": category.en_name,
            "total_words": words_in_category,
            "memorized_words": memorized_words
        })
    Session.remove()
    return render_template("statistic.html", statistic=statistic, user=user)


@app.route("/")
@authenticate
def root(user, *args, **kwargs):
    """Root page"""
    return redirect("/category")


@app.route("/login", methods=['GET', 'POST'])
def login(*args, **kwargs):
    """Login page"""
    if request.method == 'GET':
        return render_template("login.html")
    else:
        session = Session()
        data = request.form
        email = data.get("email")
        password = data.get("password")
        password_hash = hashlib.md5(password.encode("utf-8")).hexdigest()
        if not email or not password:
            return render_template("error.html", error="Email or Password is absent")

        result = session.query(User).where(User.email == email, User.password == password_hash).all()

        if not result:
            Session.remove()
            return render_template("error.html", error="Invalid Email or Password")
        else:
            resp = make_response(redirect("/category"))
            resp.set_cookie("token", result[0].token)
            Session.remove()
            return resp


@app.route("/register", methods=['GET', 'POST'])
def register(*args, **kwargs):
    """Register page"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        session = Session()
        data = request.form
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        surname = data.get("surname")
        password_hash = hashlib.md5(password.encode("utf-8")).hexdigest()

        result = session.query(User).where(User.email == email).all()
        if result:
            Session.remove()
            return render_template("error.html", error="You can't use this email, choose another one")

        if not any([email, password, name, surname]):
            Session.remove()
            return render_template("error.html", error="Data for registration is not full")

        token = str(uuid.uuid4())
        try:
            instance = User(name=name, surname=surname, password=password_hash, email=email, token=token)
            session.add(instance)
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            Session.remove()
            return render_template("error.html", error="An error occurred while creating new user")

        resp = make_response(redirect("/category"))
        resp.set_cookie("token", token)
        Session.remove()
        return resp


@app.route("/logout")
def logout(*args, **kwargs):
    """Logout page"""
    resp = make_response(redirect("/login"))
    resp.set_cookie("token", "")
    return resp


if __name__ == "__main__":
    print("Launched!")
    serve(app, host="0.0.0.0", port=5001, threads=6)
