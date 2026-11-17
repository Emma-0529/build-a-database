import os

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
    for i, item in enumerate(self.index):
      if item[0] == key:
        return i
    return -1

  def set(self, key, value):
    if self.in_transaction:
      self.tx_buffer.append(("SET", key, value))
      return "QUEUED"
    return self._commit_set(key, value)

  def _commit_set(self, key, value):
    # "last write wins" semantics
    idx = self._find(key)
    if idx != -1:
      self.index[idx][1] = value
    else:
      self.index.append([key, value])
    self._append_log(f"SET {key} {value}\n")
    return "OK"

  def get(self, key):
    # GET command - basic requirement
    idx = self._find(key)
    if idx != -1:
      return self.index[idx][1]
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
    val = int(self.index[idx][1]) if idx != -1 and self.index[idx][1].isdigit() else 0
    val += 1
    self.set(key, str(val))
    return str(val)

  def decr(self, key):
    # DECR command - counters requirement
    idx = self._find(key)
    val = int(self.index[idx][1]) if idx != -1 and self.index[idx][1].isdigit() else 0
    val -= 1
    self.set(key, str(val))
    return str(val)

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
          idx = self._find(parts[1])
          if idx != -1:
            self.index[idx][1] = parts[2]
          else:
            self.index.append([parts[1], parts[2]])
        elif cmd == "DEL" and len(parts) == 2:
          idx = self._find(parts[1])
          if idx != -1:
            self.index.pop(idx)
        elif cmd == "FLUSHDB":
          self.index = []