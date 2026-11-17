import os
import unittest
from database import DATA_FILE, Database


class TestDatabase(unittest.TestCase):

  def setUp(self):
    # interval test setup
    if os.path.exists(DATA_FILE):
      os.remove(DATA_FILE)
    self.db = Database()

  def test_set_and_get(self):
    # test basic SET and GET commands
    self.assertEqual(self.db.set("foo", "bar"), "OK")
    self.assertEqual(self.db.get("foo"), "bar")

  def test_persistence(self):
    # test data consistency / log replay on restart
    self.db.set("persist_key", "value123")
    db_reloaded = Database()
    db_reloaded.load_log()
    self.assertEqual(db_reloaded.get("persist_key"), "value123")

  def test_transactions(self):
    # test transaction commands
    self.db.begin()
    self.db.set("t_key", "t_val")
    self.assertEqual(self.db.get("t_key"), "t_val")
    self.db.commit()
    self.assertEqual(self.db.get("t_key"), "t_val")

  def tearDown(self):
    # test cleanup
    if os.path.exists(DATA_FILE):
      os.remove(DATA_FILE)


if __name__ == "__main__":
  unittest.main()