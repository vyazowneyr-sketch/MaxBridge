from __future__ import annotations

import re

import pytest

from maxbridge.application.services import generate_public_id


def test_generate_public_id_has_exact_safe_length() -> None:
    public_id = generate_public_id(32)

    assert len(public_id) == 32
    assert re.fullmatch(r"[A-Za-z0-9]+", public_id)


def test_generate_public_id_rejects_invalid_length() -> None:
    with pytest.raises(ValueError):
        generate_public_id(0)
