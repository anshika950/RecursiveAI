"""Shared Limiter instance.

Lives in its own module (rather than app/main.py) so router modules can
import it for @limiter.limit(...) decorators without a circular import
(app.main imports the routers; the routers would otherwise need to
import app.main to get the limiter).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
