from flask import request, redirect
from models import session, User


def authenticate(called_func):
    def wrap(*args, **kwargs):
        token = request.cookies.get('token')
        result = session.query(User).where(User.token == token).all()
        if result:
            result = result[0]
            user = {"id": result.id, "name": result.name, "surname": result.surname}
        else:
            return redirect("/login")
        return called_func(user=user, *args, **kwargs)

    wrap.__name__ = called_func.__name__
    return wrap
