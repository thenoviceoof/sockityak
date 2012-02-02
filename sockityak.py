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

import time
import json
import os
import hashlib
from operator import itemgetter

################################################################################
# sessions

# default is an hour
DEFAULT_SESSION_LIFETIME = 24*3600

# session object, through which we fetch data
class RedisSession():
    def __init__(self, request, redis_connection=None):
        # get the request ip address, and session cookie
        ip = request.request.remote_ip
        session = request.get_cookie("session")
        self.request = request
        # if there's no session cookie, generate one
        print(ip)
        print(session)
        if not session:
            # use the given cookie_secret
            salt = request.settings.get("cookie_secret") + ip
            session = self.generate_sessionid(salt)
            print(session)
            # !!! figure out how to break this out into settings
            request.set_cookie("session", session, expires_days=1./24)
        self.prefix = "session:%s:%s" % (session, ip)
        print(self.prefix)
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
        """delete the session cookie"""
        self.request.set_cookie("session", "", expires=0)
    def generate_sessionid(self, salt):
        """Creates a unique session"""
        return hashlib.sha1(salt+str(time.time())).hexdigest()
    def redis_key(self, key):
        """Little utility function to provide consistent key building"""
        return self.prefix + ":" + key
    def get(self, key, default=None):
        print(self.redis_key(key))
        return (self.redis.get(self.redis_key(key)) or default)
    # support the usual array notation
    def __getitem__(self, key):
        value = self.get(self.redis_key(key))
        if not value:
            raise KeyError
        return value
    def __setitem__(self, key, value):
        k = self.redis_key(key)
        self.redis.set(k, value)
        self.redis.expire(k, self.lifetime)
    def __delitem__(self, key):
        self.redis.delete(self.redis_key(key))
    # ! does NOT support iterators: this means storing keys in a root set
    # ! and no one cares (__len__, __iter__)

class SessionRequestHandler(tornado.web.RequestHandler):
    def get_session(self):
        rs = RedisSession(self)
        return rs

################################################################################
# HTML page handlers (mostly)

class MainHandler(SessionRequestHandler):
    def get(self):
        session = self.get_session()
        user = session.get("user")
        if user:
            r = redis.Redis(host="localhost",port=6379,db=0)
            key = "channels" # set of channel names
            channels = r.smembers(key)
            # channels.sort(key=itemgetter(1)) # need to get channel age
            self.render("templates/list.html", channels=channels)
        else:
            self.render("templates/index.html")

class ChannelHandler(SessionRequestHandler):
    def get(self, channel):
        # note: StrictRedis is not available
        r = redis.Redis(host="localhost",port=6379,db=0)
        r.sadd("channels", channel)
        key = "channel:%s" % channel
        posts = [json.loads(p) for p in r.lrange(key, -10, -1)]
        user = self.get_cookie("uname")
        self.render("templates/channel.html",
                    posts=posts, channel=channel, user=user)

################################################################################
# Auth

# mostly copy-pasted
class GoogleHandler(SessionRequestHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    def _on_auth(self, user):
        if not user:
            raise tornado.web.HTTPError(500, "Google auth failed")
        
        # shove information into a session
        session = self.get_session()
        session["user"] = user["email"]
        if user["name"]:
            session["uname"] = user["name"].replace(" ","_")
        else:
            session["uname"] = user["email"]
        # save the user data
        r = redis.Redis(host="localhost",port=6379,db=0)
        key = "user:%s" % user["email"]
        r.set(key, user["name"])

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

# whether or not we should use a multithreaded model or not
DEBUG = True

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

class EchoWebSocket(tornado.websocket.WebSocketHandler):
    def open(self, channel):
        print("WebSocket opened")
        self.channel = channel

        # add to connections dict
        conns = connections.setdefault(channel, set())
        conns.add(self)
        self.conns = conns

    # request for sending out chats
    def recieve_chat(self, message):
        r = redis.Redis(host="localhost",port=6379,db=0)
        key = "channel:%s" % self.channel
        msg = {"mess":message, "user":self.user,
               "line":-1, "time": current_ms()}

        j = json.dumps(msg)
        length = r.rpush(key, j)
        msg["line"] = length
        j = json.dumps(msg)
        r.lset(key, length-1, j)

        # publish
        if DEBUG:
            for conn in self.conns:
                conn.send_msg(j)
        else:
            pub_channel = "pub:%s" % self.channel
            r.publish(pub_channel, j)
    # handle a request for old chats
    def fetch_old(self, first_index):
        r = redis.Redis(host="localhost",port=6379,db=0)
        key = "channel:%s" % self.channel
        # out of index does not produce errors
        posts = r.lrange(key, first_index - 11, first_index - 2)
        print(posts)
        for post in posts:
            self.write_message(post)

    def on_message(self, mess):
        d = json.loads(mess)
        t = d["type"]
        message = d["message"]

        if t == "mess":
            self.recieve_chat(message)
        elif t == "old":
            self.fetch_old(message)
        else:
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
    (r"/channel/(\w+)", ChannelHandler),
    (r"/websocket/(\w+)", EchoWebSocket),    
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
