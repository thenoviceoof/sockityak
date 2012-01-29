#!/usr/bin/python
################################################################################

import tornado.ioloop
import tornado.web
import tornado.template
import tornado.websocket

import redis

import threading

import time
import json
import os
from operator import itemgetter

################################################################################

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        r = redis.Redis(host="localhost",port=6379,db=0)
        key = "channels" # set of channel names
        channels = r.smembers(key)
        # channels.sort(key=itemgetter(1)) # need to get channel age
        self.render("templates/index.html", channels=channels)

class ChannelHandler(tornado.web.RequestHandler):
    def get(self, channel):
        # note: StrictRedis is not available
        r = redis.Redis(host="localhost",port=6379,db=0)
        r.sadd("channels", channel)
        key = "channel:%s" % channel
        posts = [json.loads(p) for p in r.lrange(key, -10, -1)]
        self.render("templates/channel.html", posts=posts, channel=channel)

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

    def on_message(self, message):
        print("Message on %s: %s" % (self.channel, message))

        r = redis.Redis(host="localhost",port=6379,db=0)
        key = "channel:%s" % self.channel
        msg = {"mess":message, "user":"User", "line":-1, "time": current_ms()}
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
    (r"/channel/(\w+)", ChannelHandler),
    (r"/websocket/(\w+)", EchoWebSocket),    
]

settings = dict(
    static_path=os.path.join(os.path.dirname(__file__), "static"),
)

application = tornado.web.Application(handlers, **settings)

if __name__ == "__main__":
    # start pubsub listening thread
    if not DEBUG:
        threading.Thread(target=pubsub_listen).start()
    # start tornado things
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
