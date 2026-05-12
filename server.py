"""Backward-compat shim — preserves `python server.py` invocation.

The actual implementation lives in muse_tts.server. This file ensures
existing users who clone the repo and run `python server.py` get the
same behavior as users who `pip install muse-tts` and run `muse-tts`.
"""
from muse_tts.server import main

if __name__ == "__main__":
    main()
