import redis

# note: StrictRedis is not available
r = redis.Redis(host="localhost",port=6379,db=0)

key = "thing:mu"
r.delete(key)
while 1:
    r.rpush(key, raw_input())
    print( r.lrange(key, -10, -1) )
