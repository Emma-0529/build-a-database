import os
import time

DATA_FILE = "data.db"


class Database:

  def __init__(self):
    # in-memory index structure
    self.index = []
    # transactions state management
    self.in_transaction = False
    self.tx_buffer = []

  def _find(self, key):
    # linear scan
    current_time = time.time()
    for i, item in enumerate(self.index):
      if item[0] == key:
        if len(item) > 2 and item[2] is not None and current_time > item[2]:
          self.index.pop(i)
          return -1
        return i
    return -1

  def set(self, key, value):
    if self.in_transaction:
      self.tx_buffer.append(("SET", key, value))
      return "QUEUED"
    return self._commit_set(key, value)

  def _commit_set(self, key, value, ttl=None):
    # "last write wins" semantics
    expiry = time.time() + float(ttl) if ttl is not None else None
    idx = self._find(key)
    if idx != -1:
      self.index[idx][1] = value
      if len(self.index[idx]) > 2:
        self.index[idx][2] = expiry
      else:
        self.index[idx].append(expiry)
    else:
      self.index.append([key, value, expiry])
    self._append_log(f"SET {key} {value}\n")
    return "OK"

  def get(self, key):
    # GET command - basic requirement
    if self.in_transaction:
      for op in reversed(self.tx_buffer):
        if op[0] == "SET" and op[1] == key:
          return op[2]
        elif op[0] == "DEL" and op[1] == key:
          return "(nil)"

    idx = self._find(key)
    if idx != -1:
      val = self.index[idx][1]
      return str(val)
    return "(nil)"

  def delete(self, key):
    if self.in_transaction:
      self.tx_buffer.append(("DEL", key))
      return "QUEUED"
    return self._commit_del(key)

  def _commit_del(self, key):
    # DEL command
    idx = self._find(key)
    if idx != -1:
      self.index.pop(idx)
      self._append_log(f"DEL {key}\n")
      return "(integer) 1"
    return "(integer) 0"

  def exists(self, key):
    # EXISTS command
    idx = self._find(key)
    return "(integer) 1" if idx != -1 else "(integer) 0"

  def incr(self, key):
    # INCR command - counters requirement
    idx = self._find(key)
    val = int(self.index[idx][1]) if idx != -1 and str(self.index[idx][1]).isdigit() else 0
    val += 1
    self.set(key, str(val))
    return str(val)

  def decr(self, key):
    # DECR command - counters requirement
    idx = self._find(key)
    val = int(self.index[idx][1]) if idx != -1 and str(self.index[idx][1]).isdigit() else 0
    val -= 1
    self.set(key, str(val))
    return str(val)

  def mset(self, pairs):
    # MSET command - multi-ops requirement
    for i in range(0, len(pairs) - 1, 2):
      self.set(pairs[i], pairs[i + 1])
    return "OK"

  def mget(self, keys):
    # MGET command - multi-ops requirement
    return [self.get(k) for k in keys]

  def expire(self, key, seconds):
    # EXPIRE command - expiration requirement
    idx = self._find(key)
    if idx != -1:
      expiry = time.time() + float(seconds)
      if len(self.index[idx]) > 2:
        self.index[idx][2] = expiry
      else:
        self.index[idx].append(expiry)
      return "(integer) 1"
    return "(integer) 0"

  def ttl(self, key):
    # TTL command - expiration requirement
    idx = self._find(key)
    if idx != -1:
      if len(self.index[idx]) > 2 and self.index[idx][2] is not None:
        remaining = int(self.index[idx][2] - time.time())
        return str(max(0, remaining))
      return "-1"
    return "-2"

  def range_keys(self, start_key, end_key):
    # RANGE command - range query requirement
    sorted_keys = sorted([item[0] for item in self.index])
    res = []
    in_range = False
    for k in sorted_keys:
      if k == start_key:
        in_range = True
      if in_range:
        res.append(k)
      if k == end_key:
        break
    return res

  def hset(self, key, field, value):
    # HSET command - hashes requirement
    idx = self._find(key)
    if idx == -1:
      self.index.append([key, [[field, value]], None])
    else:
      if not isinstance(self.index[idx][1], list):
        self.index[idx][1] = []
      found = False
      for f in self.index[idx][1]:
        if f[0] == field:
          f[1] = value
          found = True
          break
      if not found:
        self.index[idx][1].append([field, value])
    self._append_log(f"HSET {key} {field} {value}\n")
    return "(integer) 1"

  def hget(self, key, field):
    # HGET command - hashes requirement
    idx = self._find(key)
    if idx != -1 and isinstance(self.index[idx][1], list):
      for f in self.index[idx][1]:
        if f[0] == field:
          return str(f[1])
    return "(nil)"

  def hgetall(self, key):
    # HGETALL command - hashes requirement
    idx = self._find(key)
    if idx != -1 and isinstance(self.index[idx][1], list):
      res = []
      for f in self.index[idx][1]:
        res.append(f[0])
        res.append(str(f[1]))
      return res
    return []

  def lpush(self, key, value):
    # LPUSH command - lists requirement
    idx = self._find(key)
    if idx == -1:
      self.index.append([key, [value], None])
    else:
      if not isinstance(self.index[idx][1], list):
        self.index[idx][1] = [value]
      else:
        self.index[idx][1].insert(0, value)
    self._append_log(f"LPUSH {key} {value}\n")
    return str(len(self.index[idx][1]))

  def rpush(self, key, value):
    # RPUSH command - lists requirement
    idx = self._find(key)
    if idx == -1:
      self.index.append([key, [value], None])
    else:
      if not isinstance(self.index[idx][1], list):
        self.index[idx][1] = [value]
      else:
        self.index[idx][1].append(value)
    self._append_log(f"RPUSH {key} {value}\n")
    return str(len(self.index[idx][1]))

  def lrange(self, key, start, stop):
    # LRANGE command - lists requirement
    idx = self._find(key)
    if idx != -1 and isinstance(self.index[idx][1], list):
      lst = self.index[idx][1]
      try:
        s = int(start)
        e = int(stop)
        e_slice = e + 1 if e >= 0 else len(lst) + e + 1
        return lst[s:e_slice]
      except:
        return lst
    return []

  def flush(self):
    # FLUSHDB command - management requirement
    self.index = []
    if os.path.exists(DATA_FILE):
      open(DATA_FILE, "w").close()
    self._append_log("FLUSHDB\n")
    return "OK"

  def begin(self):
    # BEGIN command - transactions requirement
    if self.in_transaction:
      return "ERR Transaction already started"
    self.in_transaction = True
    self.tx_buffer = []
    return "OK"

  def commit(self):
    # COMMIT command - transactions requirement
    if not self.in_transaction:
      return "ERR No transaction active"
    for op in self.tx_buffer:
      if op[0] == "SET":
        self._commit_set(op[1], op[2])
      elif op[0] == "DEL":
        self._commit_del(op[1])
    self.in_transaction = False
    self.tx_buffer = []
    return "OK"

  def abort(self):
    # ABORT command - transactions requriement
    if not self.in_transaction:
      return "ERR No transaction active"
    self.in_transaction = False
    self.tx_buffer = []
    return "OK"

  # append-only disk write to data.db
  def _append_log(self, text):
    with open(DATA_FILE, "a") as f:
      f.write(text)
      f.flush()
      os.fsync(f.fileno())

  # replay log to rebuild in-memory index on startup
  def load_log(self):
    if not os.path.exists(DATA_FILE):
      return
    with open(DATA_FILE, "r") as f:
      for line in f:
        line = line.strip()
        if not line:
          continue
        parts = line.split(" ", 2)
        cmd = parts[0].upper()
        if cmd == "SET" and len(parts) == 3:
          sub = parts[2].split(" ", 1)
          self._commit_set(parts[1], sub[0] if len(sub) == 1 else parts[2])
        elif cmd == "DEL" and len(parts) == 2:
          self._commit_del(parts[1])
        elif cmd == "HSET" and len(parts) == 3:
          sub = parts[2].split(" ", 1)
          if len(sub) == 2:
            self.hset(parts[1], sub[0], sub[1])
        elif cmd == "LPUSH" and len(parts) == 3:
          sub = parts[2].split(" ", 1)
          if len(sub) == 2:
            self.lpush(parts[1], sub[1])
        elif cmd == "FLUSHDB":
          self.index = []