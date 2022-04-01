import hashlib
import random
import uuid

import sqlalchemy
from flask import Response, Flask, render_template, redirect, make_response, request, send_from_directory
from sqlalchemy import or_, func
from waitress import serve

from decorators import authenticate
from models import User, Category, Word, Statistic, session

app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route("/category", methods=["GET"])
@authenticate
def category(user, *args, **kwargs):
    """Function returns all existing categories"""
    categories = []
    all_categories = session.query(Category).all()
    for category in all_categories:
        categories.append({"id": category.id, "ru_name": category.ru_name, "en_name": category.en_name,
                           "image": category.image})
    return render_template("category.html", categories=categories, user=user)


@app.route("/category/<int:category_id>", methods=["GET"])
@authenticate
def word(user, category_id, *args, **kwargs):
    """Function returns <count> words from category <category_id>"""
    try:
        count = int(request.args.get("count"))
    except ValueError:
        count = 10
    except TypeError:
        count = 10

    words = []
    all_words = []
    new_or_memorized_words = session.query(Word).join(Statistic, Word.id == Statistic.word_id, isouter=True).filter(
        Word.category_id == category_id, or_(Statistic.is_memorized == None, Statistic.is_memorized == True),
        or_(Statistic.user_id == None, Statistic.user_id == user["id"])).all()

    forgotten_words = session.query(Word).join(Statistic, Word.id == Statistic.word_id, isouter=True).filter(
        Word.category_id == category_id, Statistic.is_memorized == False,
        or_(Statistic.user_id == None, Statistic.user_id == user["id"])).all()

    new_or_memorized_words_count = count // 2
    forgotten_words_count = count - new_or_memorized_words_count

    if len(forgotten_words) < forgotten_words_count:
        forgotten_words_count = len(forgotten_words)
        new_or_memorized_words_count = count - forgotten_words_count

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
    try:
        data = request.get_json()
    except Exception:
        return Response('{"message": "Не удалось десериализовать данные"}', status=400, mimetype='application/json')

    word_id = data.get("word_id")
    is_memorized = data.get("is_memorized")

    if word_id is None or is_memorized is None:
        return Response('{"message": "Отсутсвует обязательный ключ"}', status=400, mimetype='application/json')

    if not isinstance(word_id, int):
        return Response('{"message": "Ключ word_id не является числом"}', status=400, mimetype='application/json')
    if not isinstance(is_memorized, bool):
        return Response('{"message": "Ключ word_id не является числом"}', status=400, mimetype='application/json')

    instance = session.query(Word).where(Word.id == word_id).first()
    if not instance:
        return Response(status=404)

    instance = session.query(Statistic).where(Statistic.word_id == word_id, Statistic.user_id == user["id"])
    if instance.first():
        instance.update({'is_memorized': is_memorized})
        session.commit()
        return Response(status=204)
    else:
        try:
            instance = Statistic(user_id=user["id"], word_id=word_id, is_memorized=is_memorized)
            session.add(instance)
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            return Response(status=500)
        return Response(status=201)


@app.route("/statistic", methods=["GET"])
@authenticate
def statistic(user, *args, **kwargs):
    """Function returns statistics for current user on learned words"""
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
            memorized_words_in_each_category[category.id] = 0
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
        data = request.form
        email = data.get("email")
        password = data.get("password")
        password_hash = hashlib.md5(password.encode("utf-8")).hexdigest()
        if not email or not password:
            return render_template("error.html", error="Email or Password is absent")

        result = session.query(User).where(User.email == email, User.password == password_hash).all()

        if not result:
            return render_template("error.html", error="Invalid Email or Password")
        else:
            resp = make_response(redirect("/category"))
            resp.set_cookie("token", result[0].token)
            return resp


@app.route("/register", methods=['GET', 'POST'])
def register(*args, **kwargs):
    """Register page"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        data = request.form
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")
        surname = data.get("surname")
        password_hash = hashlib.md5(password.encode("utf-8")).hexdigest()

        result = session.query(User).where(User.email == email).all()
        if result:
            return render_template("error.html", error="You can't use this email, choose another one")

        if not any([email, password, name, surname]):
            return render_template("error.html", error="Data for registration is not full")

        token = str(uuid.uuid4())
        try:
            instance = User(name=name, surname=surname, password=password_hash, email=email, token=token)
            session.add(instance)
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            return render_template("error.html", error="An error occurred while creating new user")

        resp = make_response(redirect("/category"))
        resp.set_cookie("token", token)
        return resp


@app.route("/logout")
def logout(*args, **kwargs):
    """Logout page"""
    resp = make_response(redirect("/login"))
    resp.set_cookie("token", "")
    return resp


if __name__ == "__main__":
    print("Launched!")
    serve(app, host="0.0.0.0", port=5001)
