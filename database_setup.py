import csv

import sqlalchemy

from models import Base, engine, Session, Category, Word

Base.metadata.create_all(engine)
session = Session()

with open("static/Categories.csv", 'r', newline='', encoding='utf-8-sig') as f:
    reader = csv.reader(f, delimiter=';')
    categories = list(reader)

for category in categories:
    try:
        record = Category(id=category[0], ru_name=category[1], en_name=category[2], image=category[3])
        session.add(record)
        session.commit()
    except sqlalchemy.exc.IntegrityError:
        session.rollback()

with open("static/Words.csv", 'r', newline='', encoding='utf-8-sig') as f:
    reader = csv.reader(f, delimiter=';')
    words = list(reader)

for word in words:
    try:
        record = Word(id=word[0], category_id=word[1], ru_name=word[2], en_name=word[3])
        session.add(record)
        session.commit()
    except sqlalchemy.exc.IntegrityError:
        session.rollback()

Session.remove()
