#!/usr/bin/python
################################################################################

import tornado.ioloop
import tornado.web

import redis

from jinja2 import Environment, FileSystemLoader

template_env = Environment(loader = FileSystemLoader('templates/'))
def render(template_path, args):
    template = template_env.get_template(template_path)
    return template.render(**args)

KEY = "STATIC"

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        # note: StrictRedis is not available
        r = redis.Redis(host="localhost",port=6379,db=0)
        posts = r.lrange(KEY, 0, -1)
        self.write(render("index.html", {"posts": posts}))
    def post(self):
        r = redis.Redis(host="localhost",port=6379,db=0)
        post = self.get_argument("post")
        r.rpush(KEY, post)
        self.redirect("/")

application = tornado.web.Application([
    (r"/", MainHandler),
])

if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
