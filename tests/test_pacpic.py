from pathlib import Path

from amos_abk import load, parse_packed_picture

DATA_DIR = Path(__file__).parent / "data"


def test_parse_screen_header():
    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    assert pic.width == 160
    assert pic.height == 10
    assert pic.num_planes == 4
    assert pic.num_colors == 16
    assert pic.display_width == 160
    assert pic.display_height == 10


def test_palette():
    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    assert len(pic.palette) == 32
    # First colour is black (background)
    assert pic.palette[0] == (0, 0, 0)
    # All entries should be valid RGB tuples
    for r, g, b in pic.palette:
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255


def test_planes_dimensions():
    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    assert len(pic.planes) == pic.num_planes
    plane_size = (pic.width // 8) * pic.height
    for plane in pic.planes:
        assert len(plane) == plane_size


def test_to_indexed_size():
    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    indexed = pic.to_indexed()
    assert len(indexed) == pic.width * pic.height


def test_to_indexed_range():
    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    indexed = pic.to_indexed()
    for idx in indexed:
        assert 0 <= idx < pic.num_colors


def test_to_rgb_size():
    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    rgb = pic.to_rgb()
    assert len(rgb) == pic.width * pic.height * 3


def test_to_rgba_size():
    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    rgba = pic.to_rgba()
    assert len(rgba) == pic.width * pic.height * 4


def test_to_rgba_transparency():
    """Palette index 0 should produce fully transparent pixels."""
    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    indexed = pic.to_indexed()
    rgba = pic.to_rgba()
    for i, idx in enumerate(indexed):
        alpha = rgba[i * 4 + 3]
        if idx == 0:
            assert alpha == 0
        else:
            assert alpha == 255


def test_decompressed_not_all_zeros():
    """The decompressed image should contain some non-zero data."""
    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    total_nonzero = sum(1 for p in pic.planes for b in p if b != 0)
    assert total_nonzero > 0


def test_flags():
    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    assert pic.flags == 0x00E2


def test_to_image():
    from PIL import Image

    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    img = pic.to_image()
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    assert img.size == (pic.width, pic.height)


def test_to_image_larger():
    from PIL import Image

    abk = load(DATA_DIR / "pacpic_320x200.abk")
    pic = parse_packed_picture(abk.banks[0].data)
    img = pic.to_image()
    assert isinstance(img, Image.Image)
    assert img.size == (320, 200)
