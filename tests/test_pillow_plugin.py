import struct
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError

import amos_abk

DATA_DIR = Path(__file__).parent / "data"


def test_open_sprites():
    img = Image.open(DATA_DIR / "multi_sprites.abk")
    assert isinstance(img, Image.Image)
    assert img.format == "ABK"
    assert img.mode == "RGBA"


def test_open_pacpic():
    img = Image.open(DATA_DIR / "pacpic_320x200.abk")
    assert img.size == (320, 200)
    assert img.mode == "RGBA"


def test_sprite_frame_count():
    img = Image.open(DATA_DIR / "multi_sprites.abk")
    assert img.n_frames == 6


def test_pacpic_single_frame():
    img = Image.open(DATA_DIR / "pacpic.abk")
    assert img.n_frames == 1
    assert not img.is_animated


def test_seek_all_frames():
    img = Image.open(DATA_DIR / "multi_sprites.abk")
    for i in range(img.n_frames):
        img.seek(i)
        img.load()
        assert img.size[0] > 0
        assert img.size[1] > 0


def _sprite_bank(*sizes):
    """A bare sprite bank of 1-plane images with the given (width_words, height) sizes."""
    data = b"AmSp" + struct.pack(">H", len(sizes))
    for w_words, h in sizes:
        data += struct.pack(">HHHHH", w_words, h, 1, 0, 0) + b"\xff" * (w_words * 2 * h)
    return data + bytes(64)


def test_seek_updates_size():
    img = Image.open(BytesIO(_sprite_bank((1, 1), (2, 3))))
    assert img.size == (16, 1)
    img.seek(1)
    assert img.size == (32, 3)
    img.seek(0)
    assert img.size == (16, 1)


def test_tell():
    img = Image.open(DATA_DIR / "multi_sprites.abk")
    assert img.tell() == 0
    img.seek(3)
    assert img.tell() == 3


def test_abk_in_info():
    img = Image.open(DATA_DIR / "multi_sprites.abk")
    assert "abk" in img.info
    assert isinstance(img.info["abk"], amos_abk.AbkFile)


def test_open_bank_set():
    img = Image.open(DATA_DIR / "basic.abk")
    assert img.format == "ABK"
    assert img.n_frames == 2


def test_non_image_bank_raises():
    """Pillow should reject banks with no image data."""
    with pytest.raises(UnidentifiedImageError):
        Image.open(DATA_DIR / "music.abk")


def test_images_from_path():
    imgs = amos_abk.images(DATA_DIR / "multi_sprites.abk")
    assert len(imgs) == 6
    for img in imgs:
        assert isinstance(img, Image.Image)
        assert img.mode == "RGBA"


def test_images_from_abk():
    abk = amos_abk.load(DATA_DIR / "multi_sprites.abk")
    imgs = amos_abk.images(abk)
    assert len(imgs) == 6


def test_images_pacpic():
    imgs = amos_abk.images(DATA_DIR / "pacpic_320x200.abk")
    assert len(imgs) == 1
    assert imgs[0].size == (320, 200)
