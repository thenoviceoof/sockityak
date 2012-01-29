#!/usr/bin/python
################################################################################

import tornado.ioloop
import tornado.web
import tornado.template
import tornado.websocket

import redis

import os

KEY = "STATIC"

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        # note: StrictRedis is not available
        r = redis.Redis(host="localhost",port=6379,db=0)
        posts = r.lrange(KEY, 0, -1)
        self.render("templates/index.html", posts= posts)
    def post(self):
        r = redis.Redis(host="localhost",port=6379,db=0)
        post = self.get_argument("post")
        r.rpush(KEY, post)
        self.redirect("/")


conns = set()
class EchoWebSocket(tornado.websocket.WebSocketHandler):
    def open(self):
        print "WebSocket opened"
        conns.add(self)

    def on_message(self, message):
        for conn in conns:
            conn.send_msg(message)

    def send_msg(self, msg):
        self.write_message(u"User: " + msg)

    def on_close(self):
        print "WebSocket closed"
        conns.remove(self)

handlers = [
    (r"/", MainHandler),
    (r"/websocket", EchoWebSocket),    
]

settings = dict(
    static_path=os.path.join(os.path.dirname(__file__), "static"),
)

application = tornado.web.Application(handlers, **settings)

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
