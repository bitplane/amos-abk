"""Pillow plugin for AMOS .abk bank files.

Registers the ABK format so that ``Image.open("file.abk")`` works
after ``import amos_abk``.

Sprite and icon banks produce one frame per image (RGBA, index 0 transparent),
skipping empty slots.
Pac.Pic. banks produce one frame per picture (RGBA, fully opaque).
Non-image banks (music, samples, amal, data) are skipped.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from io import BytesIO

from PIL import Image, ImageFile

from amos_abk.bank import AbkFile
from amos_abk.bank import load as _load_abk
from amos_abk.pacpic import _packed_picture_size, parse_packed_picture
from amos_abk.sprite import parse_sprites

# Bank names that contain parseable image data
_SPRITE_NAMES = {"Sprites", "Icons"}

# A frame's size, and a function that decodes it
_FrameSource = tuple[tuple[int, int], Callable[[], Image.Image]]


def _accept(prefix):
    return prefix[:4] in (b"AmBk", b"AmBs", b"AmSp", b"AmIc")


def _packed_picture_image(data: bytes) -> Image.Image:
    pic = parse_packed_picture(data)
    return Image.frombytes("RGBA", (pic.width, pic.height), pic.to_rgba())


def _frame_sources(abk: AbkFile) -> list[_FrameSource]:
    """Find every image in every bank, in bank order, without decoding pixels."""
    sources = []
    for bank in abk.banks:
        if bank.name in _SPRITE_NAMES:
            for sprite in parse_sprites(bank.data):
                # Deleted images are stored as empty slots; there's nothing to show
                if sprite.width and sprite.height:
                    sources.append(((sprite.width, sprite.height), sprite.to_image))
        elif bank.name == "Pac.Pic.":
            sources.append((_packed_picture_size(bank.data), partial(_packed_picture_image, bank.data)))
    return sources


def _build_frames(abk: AbkFile) -> list[Image.Image]:
    """Extract all images from all banks, in bank order."""
    return [decode() for _size, decode in _frame_sources(abk)]


def images(source) -> list[Image.Image]:
    """Extract all images from an ABK file.

    Args:
        source: file path (str/Path), bytes, a binary stream, or an already-loaded AbkFile.

    Returns:
        List of PIL Images (RGBA). Sprites and icons get one image each,
        packed pictures get one image. Non-image banks and empty sprite
        slots are skipped, so use parse_sprites() when AMOS image numbers
        matter.
    """
    if isinstance(source, AbkFile):
        return _build_frames(source)
    return _build_frames(_load_abk(source))


class AmosAbkFile(ImageFile.ImageFile):
    format = "ABK"
    format_description = "AMOS Memory Bank"

    def _open(self):
        self.fp.seek(0)
        # Pillow only turns SyntaxError into UnidentifiedImageError
        try:
            abk = _load_abk(BytesIO(self.fp.read()))
            self._sources = _frame_sources(abk)
        except ValueError as exc:
            raise SyntaxError(str(exc)) from exc
        self.info["abk"] = abk

        if not self._sources:
            raise SyntaxError("No image data in ABK file")

        # Every frame is RGBA; pixels are decoded on load()
        self._loaded_frame = None
        self._frame = 0
        self._n_frames = len(self._sources)
        self.is_animated = self._n_frames > 1
        self._size = self._sources[0][0]
        self._mode = "RGBA"

    @property
    def n_frames(self):
        return self._n_frames

    def seek(self, frame):
        if not self._seek_check(frame):
            return
        Image._decompression_bomb_check(self._sources[frame][0])
        self._frame = frame
        self._size = self._sources[frame][0]

    def tell(self):
        return self._frame

    def load(self):
        if self._frame >= self._n_frames:
            raise EOFError("no more frames")
        if self._loaded_frame != self._frame:
            try:
                decoded = self._sources[self._frame][1]()
            except ValueError as exc:
                raise OSError(str(exc)) from exc
            self.im = decoded.im
            self._loaded_frame = self._frame
        if self._n_frames == 1 and self.fp is not None:
            if self._exclusive_fp:
                self.fp.close()
            self.fp = None
        return Image.Image.load(self)


Image.register_open(AmosAbkFile.format, AmosAbkFile, _accept)
Image.register_extension(AmosAbkFile.format, ".abk")
