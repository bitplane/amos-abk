from pathlib import Path

from amos_abk import load, parse_sprites

DATA_DIR = Path(__file__).parent / "data"


def test_parse_single_sprite():
    abk = load(DATA_DIR / "sprites.abk")
    sprites = parse_sprites(abk.banks[0].data)
    assert len(sprites) == 1
    s = sprites[0]
    assert s.width == 16
    assert s.height == 1
    assert s.num_planes == 4
    assert s.num_colors == 16
    assert s.hotspot_x == 0
    assert s.hotspot_y == 0


def test_parse_single_icon():
    abk = load(DATA_DIR / "icons.abk")
    sprites = parse_sprites(abk.banks[0].data)
    assert len(sprites) == 1
    s = sprites[0]
    assert s.width == 16
    assert s.height == 1
    assert s.num_planes == 4


def test_parse_multi_sprites():
    abk = load(DATA_DIR / "multi_sprites.abk")
    sprites = parse_sprites(abk.banks[0].data)
    assert len(sprites) == 6
    for s in sprites:
        assert s.width == 16
        assert s.height == 16
        assert s.num_planes == 2
        assert s.num_colors == 4


def test_palette_parsing():
    abk = load(DATA_DIR / "sprites.abk")
    sprites = parse_sprites(abk.banks[0].data)
    palette = sprites[0].palette
    assert len(palette) == 32
    # First color should be (0, 0, 0) - transparent/background
    assert palette[0] == (0, 0, 0)
    # All entries should be valid RGB tuples
    for r, g, b in palette:
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255


def test_to_indexed():
    abk = load(DATA_DIR / "multi_sprites.abk")
    sprites = parse_sprites(abk.banks[0].data)
    s = sprites[0]
    indexed = s.to_indexed()
    assert len(indexed) == s.width * s.height
    # All indices should be within the colour range
    for idx in indexed:
        assert 0 <= idx < s.num_colors


def test_to_rgb():
    abk = load(DATA_DIR / "multi_sprites.abk")
    sprites = parse_sprites(abk.banks[0].data)
    s = sprites[0]
    rgb = s.to_rgb()
    assert len(rgb) == s.width * s.height * 3


def test_to_rgba():
    abk = load(DATA_DIR / "multi_sprites.abk")
    sprites = parse_sprites(abk.banks[0].data)
    s = sprites[0]
    rgba = s.to_rgba()
    assert len(rgba) == s.width * s.height * 4


def test_to_rgba_transparency():
    """Palette index 0 should produce fully transparent pixels."""
    abk = load(DATA_DIR / "multi_sprites.abk")
    sprites = parse_sprites(abk.banks[0].data)
    s = sprites[0]
    indexed = s.to_indexed()
    rgba = s.to_rgba()
    for i, idx in enumerate(indexed):
        alpha = rgba[i * 4 + 3]
        if idx == 0:
            assert alpha == 0
        else:
            assert alpha == 255


def test_planes_stored_separately():
    abk = load(DATA_DIR / "multi_sprites.abk")
    sprites = parse_sprites(abk.banks[0].data)
    s = sprites[0]
    assert len(s.planes) == s.num_planes
    plane_size = (s.width // 8) * s.height
    for plane in s.planes:
        assert len(plane) == plane_size
