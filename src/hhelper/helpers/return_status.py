from enum import Enum

# FAILED means nothing was written; the menu waits for a key as with WAIT
STATUS = Enum("STATUS", ["WAIT", "NOWAIT", "FAILED"])
