"""Pillow plugin for AMOS .abk bank files.

Registers the ABK format so that ``Image.open("file.abk")`` works
after ``import amos_abk``.

Sprite and icon banks produce one frame per image (RGBA, index 0 transparent).
Pac.Pic. banks produce one frame per picture (RGBA).
Non-image banks (music, samples, amal, data) are skipped.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageFile

from amos_abk.bank import AbkFile
from amos_abk.bank import load as _load_abk
from amos_abk.pacpic import parse_packed_picture
from amos_abk.sprite import parse_sprites

# Bank names that contain parseable image data
_SPRITE_NAMES = {"Sprites", "Icons"}


def _accept(prefix):
    return prefix[:4] in (b"AmBk", b"AmSp", b"AmIc")


def _build_frames(abk: AbkFile) -> list[Image.Image]:
    """Extract all images from all banks, in bank order."""
    frames = []
    for bank in abk.banks:
        if bank.name in _SPRITE_NAMES:
            for sprite in parse_sprites(bank.data):
                frames.append(sprite.to_image())
        elif bank.name == "Pac.Pic.":
            pic = parse_packed_picture(bank.data)
            frames.append(pic.to_image().convert("RGBA"))
    return frames


def images(source) -> list[Image.Image]:
    """Extract all images from an ABK file.

    Args:
        source: file path (str/Path), BytesIO, or an already-loaded AbkFile.

    Returns:
        List of PIL Images (RGBA). Sprites and icons get one image each,
        packed pictures get one image. Non-image banks are skipped.
    """
    if isinstance(source, AbkFile):
        return _build_frames(source)
    return _build_frames(_load_abk(source))


class AmosAbkFile(ImageFile.ImageFile):
    format = "ABK"
    format_description = "AMOS Memory Bank"

    def _open(self):
        self.fp.seek(0)
        abk = _load_abk(BytesIO(self.fp.read()))
        self.info["abk"] = abk

        self._frames = _build_frames(abk)
        if not self._frames:
            raise SyntaxError("No image data in ABK file")

        self._frame = 0
        self._n_frames = len(self._frames)
        self.is_animated = self._n_frames > 1
        first = self._frames[0]
        self._size = first.size
        self._mode = first.mode

    @property
    def n_frames(self):
        return self._n_frames

    def seek(self, frame):
        if not self._seek_check(frame):
            return
        self._frame = frame

    def tell(self):
        return self._frame

    def load(self):
        if self._frame >= len(self._frames):
            raise EOFError("no more frames")
        im = self._frames[self._frame]
        self.im = im.im.copy()
        self._size = im.size
        self._mode = im.mode
        return self.im


Image.register_open(AmosAbkFile.format, AmosAbkFile, _accept)
Image.register_extension(AmosAbkFile.format, ".abk")
