import struct
from pathlib import Path

import pytest

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
    assert pic.screen_width == 160
    assert pic.screen_height == 10


def test_bare_bitmap_screen_size_from_bitmap():
    abk = load(DATA_DIR / "pacpic_320x200.abk")
    pic = parse_packed_picture(abk.banks[0].data[90:])
    assert (pic.screen_width, pic.screen_height) == (320, 200)


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


@pytest.mark.parametrize("name, bplcon0", [("pacpic.abk", 0x4200), ("pacpic_320x200.abk", 0x3000)])
def test_flags(name, bplcon0):
    """flags holds the screen's BPLCON0 value (plane count in bits 12-14, colour in bit 9)."""
    abk = load(DATA_DIR / name)
    pic = parse_packed_picture(abk.banks[0].data)
    assert pic.flags == bplcon0


def test_bare_bitmap_guesses_flags():
    abk = load(DATA_DIR / "pacpic.abk")
    bare = abk.banks[0].data[90:]
    pic = parse_packed_picture(bare)
    assert pic.flags == 0x4200


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


def test_rejects_excessive_decompressed_size():
    data = bytearray(27)
    struct.pack_into(">IHHHHHHII", data, 0, 0x06071963, 0, 0, 0xFFFF, 0xFFFF, 0xFFFF, 8, 24, 25)

    with pytest.raises(ValueError, match="too large"):
        parse_packed_picture(bytes(data))


def test_rejects_invalid_stream_offsets():
    data = bytearray(27)
    struct.pack_into(">IHHHHHHII", data, 0, 0x06071963, 0, 0, 1, 1, 1, 1, 99, 25)

    with pytest.raises(ValueError, match="Invalid RLEDATA offset"):
        parse_packed_picture(bytes(data))


def test_truncated_compressed_data_raises_value_error():
    data = bytearray(27)
    struct.pack_into(">IHHHHHHII", data, 0, 0x06071963, 0, 0, 1, 1, 129, 1, 24, 25)

    with pytest.raises(ValueError, match="Truncated Pac.Pic"):
        parse_packed_picture(bytes(data))


def test_bare_bitmap_greyscale_palette():
    abk = load(DATA_DIR / "pacpic.abk")
    pic = parse_packed_picture(abk.banks[0].data[90:])
    greys = [r for r, g, b in pic.palette[:16]]
    assert greys[0] == 0
    assert greys[15] == 255
    assert greys == sorted(greys)
    assert all(r == g == b for r, g, b in pic.palette)
