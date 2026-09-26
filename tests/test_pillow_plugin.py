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


def test_empty_sprite_slots_skipped():
    raw = _sprite_bank((0, 0), (2, 3), (0, 0))
    imgs = amos_abk.images(BytesIO(raw))
    assert [img.size for img in imgs] == [(32, 3)]

    img = Image.open(BytesIO(raw))
    assert img.n_frames == 1
    assert img.size == (32, 3)


def test_only_empty_sprite_slots_raises():
    with pytest.raises(UnidentifiedImageError):
        Image.open(BytesIO(_sprite_bank((0, 0))))


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


@pytest.mark.parametrize("name", ["pacpic.abk", "multi_sprites.abk", "basic.abk"])
def test_truncated_file_raises_unidentified(name):
    raw = (DATA_DIR / name).read_bytes()
    with pytest.raises(UnidentifiedImageError):
        Image.open(BytesIO(raw[:60]))


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


def test_open_does_not_decode(monkeypatch):
    from amos_abk import pillow_plugin

    calls = []
    real = pillow_plugin.parse_packed_picture
    monkeypatch.setattr(pillow_plugin, "parse_packed_picture", lambda data: calls.append(1) or real(data))

    img = Image.open(DATA_DIR / "pacpic_320x200.abk")
    assert img.size == (320, 200)
    assert calls == []

    img.load()
    img.load()
    assert calls == [1]


def test_frames_match_images_after_seeking():
    expected = [im.tobytes() for im in amos_abk.images(DATA_DIR / "multi_sprites.abk")]
    img = Image.open(DATA_DIR / "multi_sprites.abk")
    for i in [0, 3, 5, 1, 0]:
        img.seek(i)
        assert img.tobytes() == expected[i]


def test_decode_error_on_load_raises_oserror():
    raw = bytearray((DATA_DIR / "pacpic.abk").read_bytes())
    # Point the POINTS stream at the last byte so decompression runs off the end
    struct.pack_into(">I", raw, 20 + 90 + 20, len(raw) - 20 - 90 - 1)
    img = Image.open(BytesIO(bytes(raw)))
    with pytest.raises(OSError, match="Truncated"):
        img.load()
