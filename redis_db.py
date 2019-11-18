import redis
import os


def connect_to_db():

    r = redis.Redis(
        host=os.environ.get['REDIS_HOST'],
        port=os.environ.get['REDIS_PORT'],
        db=0,
        password=os.environ.get['REDIS_PASWORD'],
        decode_responses=True
    )
    return r
