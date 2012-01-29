#!/usr/bin/python
################################################################################

import tornado.ioloop
import tornado.web
import tornado.template
import tornado.websocket

import redis

import os
from operator import itemgetter

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        channels = [(name,len(conns))
                    for (name, conns) in connections.iteritems()]
        channels.sort(key=itemgetter(1))
        self.render("templates/index.html", channels=channels)

class ChannelHandler(tornado.web.RequestHandler):
    def get(self, channel):
        # note: StrictRedis is not available
        r = redis.Redis(host="localhost",port=6379,db=0)
        key = "channel:%s" % channel
        posts = r.lrange(key, 0, -1)
        self.render("templates/channel.html", posts=posts, channel=channel)

connections = {}
class EchoWebSocket(tornado.websocket.WebSocketHandler):
    def open(self, channel):
        print "WebSocket opened"
        self.channel = channel
        conns = connections.setdefault(channel, set())
        conns.add(self)
        self.conns = conns

    def on_message(self, message):
        print("Message on %s: %s" % (self.channel, message))

        r = redis.Redis(host="localhost",port=6379,db=0)
        key = "channel:%s" % self.channel
        r.rpush(key, message)

        for conn in self.conns:
            conn.send_msg(message)

    def send_msg(self, msg):
        self.write_message(msg)

    def on_close(self):
        print "WebSocket closed"
        self.conns.remove(self)

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
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
