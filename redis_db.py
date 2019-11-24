import redis
import os
import json


def connect_to_db():

    r = redis.Redis(
        host=os.environ.get['REDIS_HOST'],
        port=os.environ.get['REDIS_PORT'],
        db=0,
        password=os.environ.get['REDIS_PASWORD'],
        decode_responses=True
    )

    return r


def write_user_info_to_db(user_id, stage, email=None):

    r = connect_to_db()
    known_user_info = r.get(user_id)
    if known_user_info is not None:
        unpacked_known_user_info = json.loads(known_user_info)
        known_email = unpacked_known_user_info['email']
    else:
        known_email = None
    if known_email is not None and email is None:
        user_data = {'stage':stage, 'email': known_email}
    else:
        user_data = {'stage':stage, 'email': email}
    packed_user_data = json.dumps(user_data)
    r.set(user_id, packed_user_data)


def fetch_email(user_id):

    r = connect_to_db()
    known_user_info = r.get(user_id)
    if known_user_info is not None:
        unpacked_known_user_info = json.loads(known_user_info)
        known_email = unpacked_known_user_info['email']
        return known_email
    else:
        return None
