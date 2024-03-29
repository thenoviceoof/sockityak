#!/usr/bin/python
################################################################################

import tornado.ioloop
import tornado.web
import tornado.template
import tornado.websocket
import tornado.auth

import redis
import asyncmongo

import threading

from bson.son import SON
from bson import ObjectId

import datetime
import time
import json
import os
import hashlib
from operator import itemgetter, attrgetter

# whether or not we should use a multithreaded model or not
# affects signin
DEBUG = True

################################################################################
# sessions

# default is an hour
DEFAULT_SESSION_LIFETIME = 24*3600

# session object, through which we fetch data
class RedisSession():
    def __init__(self, request, session=None, redis_connection=None):
        # get the request ip address, and session cookie
        ip = request.request.remote_ip
        if not session:
            session = request.get_cookie("session")
        self.request = request
        # if there's no session cookie, generate one
        if not session:
            # use the given cookie_secret
            salt = request.settings.get("cookie_secret") + ip
            session = self.generate_sessionid(salt)
            # !!! figure out how to break this out into settings
            request.set_cookie("session", session, expires_days=1./24)
        self.prefix = "session:%s:%s" % (session, ip)
        # fill out the wanted lifetime
        self.lifetime = request.settings.get("session_lifetime",
                                             DEFAULT_SESSION_LIFETIME)
        if redis_connection:
            self.redis = redis_connection
        else:
            # default redis connection
            # !!! possibly build out of application.settings
            self.redis = redis.Redis(host="localhost",port=6379,db=0)
    def terminate(self):
        """delete the session cookie, unset the redis session"""
        keys = list(self.redis.smembers(self.redis_key()))
        self.redis.delete(self.redis_key())
        for key in keys:
            self.redis.delete(self.redis_key(key))
        self.request.set_cookie("session", "", expires=0)
    def generate_sessionid(self, salt):
        """Creates a unique session"""
        return hashlib.sha1(salt+str(time.time())).hexdigest()
    def redis_key(self, key=None):
        """Little utility function to provide consistent key building"""
        if key:
            return self.prefix + ":" + key
        else:
            return self.prefix
    def get(self, key, default=None):
        return (self.redis.get(self.redis_key(key)) or default)
    # support the usual array notation
    def __getitem__(self, key):
        value = self.get(self.redis_key(key))
        if not value:
            raise KeyError
        return value
    def __setitem__(self, key, value):
        k = self.redis_key(key)
        self.redis.sadd(self.redis_key(), key)
        self.redis.set(k, value)
        self.redis.expire(k, self.lifetime)
    def __delitem__(self, key):
        self.redis.srem(self.redis_key(), key)
        self.redis.delete(self.redis_key(key))
    # ! does NOT support iterators: this means storing keys in a root set
    # ! and no one cares (__len__, __iter__)

class SessionRequestHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        if not hasattr(self, '_db'):
            self._db = asyncmongo.Client(pool_id="sock",
                                         host='127.0.0.1', port=27017,
                                         maxcached=10, maxconnections=50,
                                         dbname="sockityak")
        return self._db

    def get_session(self, session=None):
        rs = RedisSession(self, session=session)
        return rs
    def check_auth(self):
        session = self.get_session()
        user = session.get("user")
        if not user:
            return False
        return True

################################################################################
# HTML page handlers (mostly)

class MainHandler(SessionRequestHandler):
    @tornado.web.asynchronous
    def get(self):
        session = self.get_session()
        user = session.get("user")
        if user:
            self.db.channels.find(callback=self._on_mongo_response)
        else:
            self.render("templates/index.html")

    def _on_mongo_response(self, response, error):
        if error:
            raise Tornado.web.HTTPError(500)
        # sort on channel age
        channels = response
        channels.sort(key=itemgetter("updated"))
        channels.reverse()
        # render out the template
        self.render("templates/list.html", channels=channels)

class AddChannelHandler(SessionRequestHandler):
    @tornado.web.asynchronous
    def get(self, channel):
        # check if the person is signed in
        if not self.check_auth():
            self.redirect("/")
            return
        self.channel = channel
        # check if the channel name is legal
        if len(channel)==0:
            self.redirect("/")
            return
        # !!! transform the channel name to be legal

        # make the channel with default values
        # _id defined to ensure uniqueness
        ch = {"_id": channel, "name": channel, "line_count": 0,
              "updated": datetime.datetime.utcnow()}
        # insert the channel
        self.db.channels.insert(ch, callback=self._on_mongo_insert)
    def _on_mongo_insert(self, response, error):
        if error:
            raise Tornado.web.HTTPError(500)
        # redirect to newly-created channel page
        self.redirect("/channel/%s" % self.channel)

class ChannelHandler(SessionRequestHandler):
    def get(self, channel):
        # check if the person is signed in
        if not self.check_auth():
            self.redirect("/")
            return
        # get the user, so the websocket can be bound
        session = self.get_session()
        user = session.get("user")
        # !! get the posts from clientside
        # render
        self.render("templates/channel.html",
                    channel=channel, user=user)

################################################################################
# Auth

class GoogleHandler(SessionRequestHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if DEBUG:
            session = self.get_session()
            session["user"] = "Larry@example.edu"
            self.redirect("/")
            return
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    @tornado.web.asynchronous
    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")
        
        # shove information into a session
        session = self.get_session()
        session["user"] = user["email"]
        # build the person's username
        name = user["first_name"]
        if user.get("last_name", None):
            name += " "+user["last_name"][0]
        if not name:
            name = user["email"]
        # save the user data
        user_dict = {"email": user["email"], "username": name}
        self.db.users.update({"email": user["email"]},
                             user_dict,
                             upsert=True, callback=self._on_mongo_response)

    def _on_mongo_response(self, response, error):
        if error:
            raise Tornado.web.HTTPError(500)
        # and redirect
        self.redirect("/")

class LogoutHandler(SessionRequestHandler):
    def get(self):
        session = self.get_session()
        session.terminate()
        self.redirect("/")

################################################################################
# websockets stuff

def current_ms():
    return int(round(time.time()*1000))

# connection pool
connections = {}

# pubsub listening thread
def pubsub_listen():
    r = redis.Redis(host="localhost",port=6379,db=0)
    p = r.pubsub()
    p.psubscribe("pub:*")
    g = p.listen()
    # waiting for published data
    d = g.next()
    while d:
        channel = d["channel"].split(":")[1]
        data = d["data"]
        for conn in connections[channel]:
            conn.send_msg(data)
        d = g.next()

class EchoWebSocket(tornado.websocket.WebSocketHandler, SessionRequestHandler):
    def open(self, channel):
        print("WebSocket opened")
        self.channel = channel

        # add to connections dict
        conns = connections.setdefault(channel, set())
        conns.add(self)
        self.conns = conns

    # handle a request for sending out a new chat
    @tornado.web.asynchronous
    def recieve_chat(self, message):
        # check signin
        if not self.session.get("user"):
            self.write_message({"type":"error", "message": "Not signed in"})
            return
        # construct the chat message
        msg = {"message":message, "user":self.user, "channel": self.channel,
               "time": current_ms()}

        # define callbacks in reverse-call order
        def _on_msg_insert(response, error):
            if error:
                self.write_message({"type":"error",
                                    "msg": "Could not save chat message"})
                return
            print(msg)
            # pubsub to subscribers
            r = redis.Redis(host="localhost",port=6379,db=0)
            j = {"type": "message", "message":msg}
            if DEBUG:
                for conn in self.conns:
                    conn.send_msg(j)
            else:
                pub_channel = "pub:%s" % self.channel
                r.publish(pub_channel, j)
        def _on_line_inc(response, error):
            # execute after line increment, prep the insert
            if error:
                self.write_message({"type":"error",
                                    "msg": "Could not increment line number"})
                return
            line_count = response["value"].get("line_count", None)
            if line_count is not None:
                msg["line"] = line_count
            # insert the message
            self.db.posts.insert(msg, callback=_on_msg_insert)

        # get the next line number, executing a findandmodify
        command = SON()
        command['findandmodify'] = 'channels'
        command['query'] = {'_id': self.channel}
        command['update'] = {'$inc': {'line_count': 1}}
        self.db.command(command, callback=_on_line_inc)

    # handle a request for old chats
    def fetch_old(self, first_index, number=None):
        # check signin
        if not self.session.get("user"):
            self.write_message({"type":"error", "message": "Not signed in"})
            return
        # callback
        def _on_mongo_fetch(response, error):
            if error:
                self.write_message({"type":"error",
                                    "msg": "Could not retrieve messages"})
                return
            messages = [{"user":r["user"], "time":r["time"],
                         "message":r["message"], "line":r["line"]}
                        for r in response]
            j = {"type":"history", "message": messages}
            self.write_message(j)
        if not number:
            number = 10
        # multiplexing on the index
        if first_index is None:
            self.db.posts.find({"channel": self.channel},
                               sort=[("line",-1)], limit=number,
                               callback=_on_mongo_fetch)
        else:
            self.db.posts.find({"channel": self.channel,
                                "line": {"$lt": int(first_index)}},
                               sort=[("line",-1)], limit=number,
                               callback=_on_mongo_fetch)
    # handle an authentication request
    def auth(self, session_token):
        session = self.get_session(session=session_token)
        self.session = session
        user = session.get("user", None)
        if user:
            self.user = user
            # !!! add us to the redis channel
            self.write_message({"type":"auth"})
        else:
            self.write_message({"type":"error", "message":"Not signed in"})

    def on_message(self, mess):
        d = json.loads(mess)
        t = d["type"]
        message = d.get("message", None)

        if t == "message":
            self.recieve_chat(message)
        elif t == "history":
            number = d.get("number", None)
            self.fetch_old(message, number)
        elif t == "auth":
            self.auth(message)
        else:
            print(message)
            raise Exception("Does not fit anything")

    def send_msg(self, msg):
        self.write_message(msg)

    def on_close(self):
        print "WebSocket closed"
        self.conns.remove(self)
        # try to clean up (possible race condition)
        if len(self.conns) == 0:
            try:
                del connections[self.channel]
            except:
                pass # don't do anything, probably a race

################################################################################
# infrastructure

handlers = [
    (r"/", MainHandler),
    (r"/auth", GoogleHandler),
    (r"/logout", LogoutHandler),
    (r"/channel/([\w-]+)", ChannelHandler),
    (r"/newchannel/([\w-]+)", AddChannelHandler),
    (r"/websocket/([\w-]+)", EchoWebSocket),    
]

settings = dict(
    static_path=os.path.join(os.path.dirname(__file__), "static"),
    cookie_secret="25c64b931ead92097fd2d435b3621dca",
    session_lifetime=24*3600,
)

application = tornado.web.Application(handlers, **settings)

if __name__ == "__main__":
    # start pubsub listening thread
    if not DEBUG:
        threading.Thread(target=pubsub_listen).start()
    # start tornado things
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
