from peewee import Model, SqliteDatabase, CharField, IntegerField, ForeignKeyField, TextField, DateTimeField, UUIDField, SQL
from datetime import datetime
import uuid

db = SqliteDatabase('diary.db')


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    uuid = UUIDField(default=uuid.uuid4, unique=True, index=True)
    phone_number = CharField(unique=True)
    

class Entry(BaseModel):
    user = ForeignKeyField(User, backref='entries')
    content = TextField()
    created = DateTimeField(constraints=[SQL('DEFAULT CURRENT_TIMESTAMP')])


def initialize_db():
    db.connect()
    db.create_tables([User, Entry], safe=True)
    db.close()