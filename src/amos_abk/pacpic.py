"""Parser for AMOS Pac.Pic. (Packed Picture) banks.

A Pac.Pic. bank contains a compressed full-screen Amiga picture with two layers:
1. A screen header (90 bytes, magic 0x12031990) with dimensions and palette
2. A packed bitmap (magic 0x06071963) using three-stream RLE compression

Reference: https://www.exotica.org.uk/wiki/AMOS_Pac.Pic._format
Reference: https://github.com/kyz/amostools (dumpamos.c)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from PIL import Image

from amos_abk.planar import MAX_PLANES, indexed_to_rgb, indexed_to_rgba, planar_to_indexed
from amos_abk.sprite import _parse_palette

# The magics are dates (12/03/1990 and 06/07/1963). The ALT variants have a
# byte zeroed; amostools' dumpamos.c accepts them too, so we do the same.
SCREEN_HEADER_MAGIC = 0x12031990
SCREEN_HEADER_MAGIC_ALT1 = 0x00031990
SCREEN_HEADER_MAGIC_ALT2 = 0x12030090
PACKED_BITMAP_MAGIC = 0x06071963
PACKED_BITMAP_MAGIC_ALT = 0x06070063

SCREEN_HEADER_SIZE = 90
# Far beyond any real Amiga screen (1024x1024x8 is 1 MiB of planes), but low
# enough that a crafted header can't make us build gigabytes of pixels.
MAX_DECOMPRESSED_SIZE = 4 * 1024 * 1024


@dataclass
class PackedPicture:
    """A decompressed packed picture from an AMOS Pac.Pic. bank."""

    width: int
    height: int
    num_planes: int
    display_width: int
    display_height: int
    flags: int
    palette: list[tuple[int, int, int]]
    planes: list[bytes]
    screen_width: int
    screen_height: int

    @property
    def num_colors(self) -> int:
        return 1 << self.num_planes

    def to_indexed(self) -> bytes:
        """Convert planar data to chunky indexed pixels (1 byte per pixel)."""
        return planar_to_indexed(self.planes, self.width, self.height)

    def to_rgb(self) -> bytes:
        """Convert to RGB pixel data (3 bytes per pixel)."""
        return indexed_to_rgb(self.to_indexed(), self.palette)

    def to_rgba(self) -> bytes:
        """Convert to RGBA pixel data (4 bytes per pixel).

        A packed picture is a full screen, so every pixel is opaque.
        """
        return indexed_to_rgba(self.to_indexed(), self.palette, transparent_index=None)

    def to_image(self) -> Image.Image:
        """Convert to a PIL Image (RGB)."""
        return Image.frombytes("RGB", (self.width, self.height), self.to_rgb())


def _decompress_bitmap(data: bytes, packed_offset: int) -> tuple[list[bytes], int, int, int]:
    """Decompress a packed bitmap from three interleaved RLE streams.

    The three streams are:
    - PICDATA: the actual pixel bytes
    - RLEDATA: 1 bit per output byte; bit=1 means read new PICDATA byte, 0=repeat
    - POINTS: 1 bit per RLEDATA byte; bit=1 means read new RLEDATA byte, 0=repeat

    Args:
        data: raw data containing the packed bitmap.
        packed_offset: offset to the packed bitmap header (0x06071963 magic).

    Returns:
        (planes, width_pixels, height, num_planes) where planes is a list of
        bytes objects, one per bitplane, in row-major order.
    """
    magic = struct.unpack_from(">I", data, packed_offset)[0]
    if magic not in (PACKED_BITMAP_MAGIC, PACKED_BITMAP_MAGIC_ALT):
        raise ValueError(f"Bad packed bitmap magic: 0x{magic:08x}")

    (_x_offset, _y_offset, width_bytes, lumps, lump_height, num_planes, rledata_offset, points_offset) = (
        struct.unpack_from(">HHHHHHII", data, packed_offset + 4)
    )

    height = lumps * lump_height
    width_pixels = width_bytes * 8

    if not width_bytes or not height or not num_planes:
        raise ValueError(f"Invalid packed bitmap dimensions: {width_pixels}x{height}, {num_planes} planes")
    if num_planes > MAX_PLANES:
        raise ValueError(f"Too many bitplanes in packed bitmap: {num_planes} (maximum {MAX_PLANES})")

    plane_size = width_bytes * height
    decompressed_size = plane_size * num_planes
    if decompressed_size > MAX_DECOMPRESSED_SIZE:
        raise ValueError(
            f"Packed bitmap is too large: {decompressed_size} decompressed bytes (maximum {MAX_DECOMPRESSED_SIZE})"
        )

    stream_start = packed_offset + 24
    for stream_name, stream_offset in (("RLEDATA", rledata_offset), ("POINTS", points_offset)):
        absolute_offset = packed_offset + stream_offset
        if absolute_offset < stream_start or absolute_offset >= len(data):
            raise ValueError(f"Invalid {stream_name} offset: {stream_offset}")

    # Stream positions (offsets are relative to packed bitmap header start)
    picdata = memoryview(data)[packed_offset + 24 :]
    rledata = memoryview(data)[packed_offset + rledata_offset :]
    points = memoryview(data)[packed_offset + points_offset :]

    # Initialise streams: first picdata and rledata bytes are read unconditionally
    pic_pos = 0
    rle_pos = 0
    pts_pos = 0

    picbyte = picdata[pic_pos]
    pic_pos += 1

    rlebyte = rledata[rle_pos]
    rle_pos += 1

    # Check first points bit (MSB); if set, read another rledata byte
    rbit = 7  # current bit position in rlebyte (MSB first)
    rrbit = 6  # current bit position in points byte (bit 7 already checked)
    if points[pts_pos] & 0x80:
        rlebyte = rledata[rle_pos]
        rle_pos += 1

    # Allocate output plane buffers
    plane_bufs = [bytearray(plane_size) for _ in range(num_planes)]

    # Decompress: iterate in plane/lump/column/row order
    for plane_idx in range(num_planes):
        for lump_idx in range(lumps):
            for col in range(width_bytes):
                for row in range(lump_height):
                    # Check rlebyte bit to decide whether to read new picdata
                    if rlebyte & (1 << rbit):
                        picbyte = picdata[pic_pos]
                        pic_pos += 1
                    rbit -= 1

                    # Write output byte
                    screen_row = lump_idx * lump_height + row
                    plane_bufs[plane_idx][screen_row * width_bytes + col] = picbyte

                    # When rlebyte is exhausted (8 bits used), check points
                    if rbit < 0:
                        rbit = 7
                        if points[pts_pos] & (1 << rrbit):
                            rlebyte = rledata[rle_pos]
                            rle_pos += 1
                        rrbit -= 1
                        if rrbit < 0:
                            rrbit = 7
                            pts_pos += 1

    return [bytes(p) for p in plane_bufs], width_pixels, height, num_planes


def _greyscale_palette(num_planes: int) -> list[tuple[int, int, int]]:
    """Fallback 32-entry palette ramping from black to white over the image's colours."""
    top = max(min(1 << num_planes, 32) - 1, 1)
    greys = [min(i * 255 // top, 255) for i in range(32)]
    return [(g, g, g) for g in greys]


def parse_packed_picture(data: bytes) -> PackedPicture:
    """Parse a Pac.Pic. bank's raw data.

    Args:
        data: the raw bank data (after AmBk header). May start with either
              a screen header (0x12031990) or a bare packed bitmap (0x06071963).

    Returns:
        A PackedPicture with decompressed bitplane data.
    """
    if len(data) < 24:
        raise ValueError(f"Pac.Pic. data too short: {len(data)} bytes")

    magic = struct.unpack_from(">I", data, 0)[0]

    if magic in (SCREEN_HEADER_MAGIC, SCREEN_HEADER_MAGIC_ALT1, SCREEN_HEADER_MAGIC_ALT2):
        if len(data) < SCREEN_HEADER_SIZE + 24:
            raise ValueError(f"Pac.Pic. data too short for screen header: {len(data)} bytes")

        screen_width, screen_height = struct.unpack_from(">HH", data, 4)
        display_width, display_height = struct.unpack_from(">HH", data, 12)
        flags = struct.unpack_from(">H", data, 20)[0]  # BPLCON0 screen mode
        palette = _parse_palette(data, 26)
        packed_offset = SCREEN_HEADER_SIZE

    elif magic in (PACKED_BITMAP_MAGIC, PACKED_BITMAP_MAGIC_ALT):
        # Bare packed bitmap without screen header
        packed_offset = 0
        num_planes_from_header = struct.unpack_from(">H", data, 14)[0]
        palette = _greyscale_palette(num_planes_from_header)
        screen_width = 0
        screen_height = 0
        display_width = 0
        display_height = 0
        # No screen mode stored, so guess BPLCON0 from the plane count (as dumpamos does)
        flags = (num_planes_from_header << 12 | 0x200) & 0xFFFF

    else:
        raise ValueError(f"Unknown Pac.Pic. magic: 0x{magic:08x}")

    try:
        planes, width_pixels, height, num_planes = _decompress_bitmap(data, packed_offset)
    except (IndexError, struct.error) as exc:
        raise ValueError("Truncated Pac.Pic. compressed data") from exc

    # Use screen header dimensions if available, otherwise derive from packed bitmap
    if screen_width == 0:
        screen_width = width_pixels
    if screen_height == 0:
        screen_height = height
    if display_width == 0:
        display_width = width_pixels
    if display_height == 0:
        display_height = height

    return PackedPicture(
        width=width_pixels,
        height=height,
        num_planes=num_planes,
        display_width=display_width,
        display_height=display_height,
        flags=flags,
        palette=palette,
        planes=planes,
        screen_width=screen_width,
        screen_height=screen_height,
    )
