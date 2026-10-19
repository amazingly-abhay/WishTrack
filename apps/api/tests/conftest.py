import pytest
import uuid

@pytest.fixture
def unique_email():
    def _generator(prefix="user"):
        return f"{prefix}_{uuid.uuid4().hex[:8]}@example.com"
    return _generator
