import redis

r = redis.Redis(host="localhost",port=6379,db=0)

r.set("thing:mu","boo")

print( r.get("thing:mu") )
