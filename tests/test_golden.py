"""Pixel-exact regression tests.

The hashes were taken from output that was checked by eye: the Pac.Pic.
files render as a font sheet and a "LETS GO!" banner.
"""

import hashlib
from pathlib import Path

import pytest

from amos_abk import load, parse_packed_picture, parse_sprites

DATA_DIR = Path(__file__).parent / "data"


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


@pytest.mark.parametrize(
    "name, expected",
    [
        ("sprites.abk", ["b1535c7783ea8829"]),
        ("icons.abk", ["59d5966c96af7eca"]),
        (
            "multi_sprites.abk",
            [
                "f40f2791d521d853",
                "3a7104a7c17f73e5",
                "2226503d05afe87e",
                "3dbde292dc958f06",
                "087d15e1891b3fea",
                "50b7c8da415b50bb",
            ],
        ),
    ],
)
def test_sprite_pixels(name, expected):
    sprites = parse_sprites(load(DATA_DIR / name).banks[0].data)
    assert [_digest(s.to_indexed()) for s in sprites] == expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("pacpic.abk", "a04ea77493508188"),
        ("pacpic_320x200.abk", "4056c7529f3092d9"),
    ],
)
def test_packed_picture_pixels(name, expected):
    pic = parse_packed_picture(load(DATA_DIR / name).banks[0].data)
    assert _digest(pic.to_indexed()) == expected
