"""Fail after real private submodules have initialized."""
import sys
from failure_state import ERRORS
from .compat.py38 import Annotated

raise ERRORS[sys.argv[1]]
