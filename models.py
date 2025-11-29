from peewee import *
import datetime

db = SqliteDatabase('videos.db')

class BaseModel(Model):
    class Meta:
        database = db

class Video(BaseModel):
    file_id = CharField(unique=True)
    caption = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)

def create_tables():
    with db:
        db.create_tables([Video])

create_tables()