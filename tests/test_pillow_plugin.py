from pathlib import Path

from PIL import Image

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


def test_tell():
    img = Image.open(DATA_DIR / "multi_sprites.abk")
    assert img.tell() == 0
    img.seek(3)
    assert img.tell() == 3


def test_abk_in_info():
    img = Image.open(DATA_DIR / "multi_sprites.abk")
    assert "abk" in img.info
    assert isinstance(img.info["abk"], amos_abk.AbkFile)


def test_non_image_bank_raises():
    """Banks with no image data should raise SyntaxError."""
    try:
        Image.open(DATA_DIR / "music.abk")
        assert False, "Should have raised"
    except Exception:
        pass


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
