"""Explicitly select unauthenticated local mode for the test process."""

import os

os.environ.setdefault("RECALLNEXT_REQUIRE_AUTH", "false")
