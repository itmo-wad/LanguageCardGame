from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, create_engine, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class AbstractBase(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_on = Column(DateTime, default=func.now())
    updated_on = Column(DateTime, default=func.now(), onupdate=func.now())


class User(AbstractBase):
    __tablename__ = 'user'

    name = Column(String(255), nullable=False)
    surname = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    password = Column(String(255), nullable=False)
    token = Column(String(36), nullable=False)


class Category(AbstractBase):
    __tablename__ = 'category'

    ru_name = Column(String(255), nullable=False)
    en_name = Column(String(255), nullable=False)
    image = Column(String(255), nullable=True)


class Word(AbstractBase):
    __tablename__ = 'word'

    category_id = Column(ForeignKey(Category.id), nullable=False)
    ru_name = Column(String(255), nullable=False)
    en_name = Column(String(255), nullable=False)


class Statistic(AbstractBase):
    __tablename__ = 'statistic'
    user_id = Column(ForeignKey(User.id), nullable=False)
    word_id = Column(ForeignKey(Word.id), nullable=False)
    is_memorized = Column(Boolean, default=False)



engine = create_engine('postgresql+psycopg2://wad-adm:StrongPassw0rd@127.0.0.1:55437/wad_db')
Session = sessionmaker(bind=engine)
session = Session()  # type: sqlalchemy.orm.Session
