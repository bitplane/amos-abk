from io import BytesIO
from pathlib import Path

import pytest

from amos_abk import load

DATA_DIR = Path(__file__).parent / "data"


def test_load_bare_sprites():
    abk = load(DATA_DIR / "sprites.abk")
    assert len(abk.banks) == 1
    bank = abk.banks[0]
    assert bank.number == 1
    assert bank.name == "Sprites"
    assert bank.memory_type == 0
    assert len(bank.data) > 0


def test_load_bare_icons():
    abk = load(DATA_DIR / "icons.abk")
    assert len(abk.banks) == 1
    bank = abk.banks[0]
    assert bank.number == 2
    assert bank.name == "Icons"
    assert len(bank.data) > 0


def test_load_ambk_music():
    abk = load(DATA_DIR / "music.abk")
    assert len(abk.banks) == 1
    bank = abk.banks[0]
    assert bank.name == "Music"
    assert bank.number == 3


def test_load_ambk_samples():
    abk = load(DATA_DIR / "samples.abk")
    assert len(abk.banks) == 1
    bank = abk.banks[0]
    assert bank.name == "Samples"
    assert bank.number == 5


def test_load_ambk_datas():
    abk = load(DATA_DIR / "datas.abk")
    assert len(abk.banks) == 1
    bank = abk.banks[0]
    assert bank.name == "Datas"
    assert bank.number == 5


def test_load_ambk_amal():
    abk = load(DATA_DIR / "amal.abk")
    assert len(abk.banks) == 1
    bank = abk.banks[0]
    assert bank.name == "Amal"
    assert bank.number == 4


def test_load_ambk_pacpic():
    abk = load(DATA_DIR / "pacpic.abk")
    assert len(abk.banks) == 1
    bank = abk.banks[0]
    assert bank.name == "Pac.Pic."
    assert bank.number == 9


def test_load_ambs_raises():
    with pytest.raises(ValueError, match="Unsupported format"):
        load(DATA_DIR / "basic.abk")


def test_load_too_short():
    from io import BytesIO

    with pytest.raises(ValueError, match="too short"):
        load(BytesIO(b"Am"))


def test_load_unknown_magic():
    from io import BytesIO

    with pytest.raises(ValueError, match="Unknown magic"):
        load(BytesIO(b"\x00\x00\x00\x00"))


def test_load_from_bytes_io():
    from io import BytesIO

    raw = (DATA_DIR / "sprites.abk").read_bytes()
    abk = load(BytesIO(raw))
    assert len(abk.banks) == 1
    assert abk.banks[0].name == "Sprites"


def test_data_matches_file_contents():
    """Bare sprite bank data should be everything after the 4-byte magic."""
    raw = (DATA_DIR / "sprites.abk").read_bytes()
    abk = load(DATA_DIR / "sprites.abk")
    assert abk.banks[0].data == raw[4:]


def test_ambk_data_matches_file_contents():
    """AmBk bank data should be everything after the 20-byte header."""
    raw = (DATA_DIR / "music.abk").read_bytes()
    abk = load(DATA_DIR / "music.abk")
    assert abk.banks[0].data == raw[20:]


def test_multi_bank_synthetic():
    """Multi-bank files don't appear in the wild corpus, so synthesize one."""
    raw_music = (DATA_DIR / "music.abk").read_bytes()
    raw_samples = (DATA_DIR / "samples.abk").read_bytes()
    combined = raw_music + raw_samples

    abk = load(BytesIO(combined))
    assert len(abk.banks) == 2
    assert abk.banks[0].name == "Music"
    assert abk.banks[1].name == "Samples"
    assert abk.banks[0].data == raw_music[20:]
    assert abk.banks[1].data == raw_samples[20:]


def test_repr():
    abk = load(DATA_DIR / "sprites.abk")
    assert "Sprites" in repr(abk)
