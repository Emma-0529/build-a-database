import sys
from database import Database


def main():
  # replay log to rebuild in-memory index on startup
  db = Database()
  db.load_log()

  # user input on STDIN and output on STDOUT
  for line in sys.stdin:
    line = line.strip()
    if not line:
      continue
    tokens = line.split(" ")
    cmd = tokens[0].upper()

    # command-line interface command router
    if cmd == "EXIT":
      break
    elif cmd == "SET" and len(tokens) >= 3:
      print(db.set(tokens[1], " ".join(tokens[2:])))
    elif cmd == "GET" and len(tokens) == 2:
      print(db.get(tokens[1]))
    elif cmd == "DEL" and len(tokens) == 2:
      print(db.delete(tokens[1]))
    elif cmd == "EXISTS" and len(tokens) == 2:
      print(db.exists(tokens[1]))
    elif cmd == "INCR" and len(tokens) == 2:
      print(db.incr(tokens[1]))
    elif cmd == "DECR" and len(tokens) == 2:
      print(db.decr(tokens[1]))
    elif cmd == "MSET" and len(tokens) >= 3:
      print(db.mset(tokens[1:]))
    elif cmd == "MGET" and len(tokens) >= 2:
      for r in db.mget(tokens[1:]):
        print(r)
    elif cmd == "EXPIRE" and len(tokens) == 3:
      print(db.expire(tokens[1], tokens[2]))
    elif cmd == "TTL" and len(tokens) == 2:
      print(db.ttl(tokens[1]))
    elif cmd == "RANGE" and len(tokens) == 3:
      for r in db.range_keys(tokens[1], tokens[2]):
        print(r)
      print("END")
    elif cmd == "HSET" and len(tokens) >= 4:
      print(db.hset(tokens[1], tokens[2], " ".join(tokens[3:])))
    elif cmd == "HGET" and len(tokens) == 3:
      print(db.hget(tokens[1], tokens[2]))
    elif cmd == "HGETALL" and len(tokens) == 2:
      res = db.hgetall(tokens[1])
      for r in res:
        print(r)
    elif cmd == "LPUSH" and len(tokens) >= 3:
      print(db.lpush(tokens[1], " ".join(tokens[2:])))
    elif cmd == "RPUSH" and len(tokens) >= 3:
      print(db.rpush(tokens[1], " ".join(tokens[2:])))
    elif cmd == "LRANGE" and len(tokens) == 4:
      for r in db.lrange(tokens[1], tokens[2], tokens[3]):
        print(r)
    elif cmd == "BEGIN":
      print(db.begin())
    elif cmd == "COMMIT":
      print(db.commit())
    elif cmd == "ABORT":
      print(db.abort())
    elif cmd == "FLUSHDB":
      print(db.flush())
    else:
      print(f"ERR unknown command '{cmd}'")


if __name__ == "__main__":
  main()