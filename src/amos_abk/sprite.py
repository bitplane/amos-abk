from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass
class Sprite:
    """A single sprite or icon image from an AMOS bank."""

    width: int
    height: int
    num_planes: int
    hotspot_x: int
    hotspot_y: int
    palette: list[tuple[int, int, int]]
    planes: list[bytes]

    @property
    def num_colors(self) -> int:
        return 1 << self.num_planes

    def to_indexed(self) -> bytes:
        """Convert planar data to chunky indexed pixels.

        Returns one byte per pixel, each byte being a palette index.
        """
        width_bytes = (self.width + 7) // 8
        row_stride = width_bytes
        result = bytearray(self.width * self.height)

        for y in range(self.height):
            for x in range(self.width):
                byte_idx = y * row_stride + x // 8
                bit = 7 - (x % 8)
                index = 0
                for plane_num in range(self.num_planes):
                    if self.planes[plane_num][byte_idx] & (1 << bit):
                        index |= 1 << plane_num
                result[y * self.width + x] = index

        return bytes(result)

    def to_rgb(self) -> bytes:
        """Convert to RGB pixel data (3 bytes per pixel)."""
        indexed = self.to_indexed()
        result = bytearray(len(indexed) * 3)
        for i, idx in enumerate(indexed):
            r, g, b = self.palette[idx] if idx < len(self.palette) else (0, 0, 0)
            result[i * 3] = r
            result[i * 3 + 1] = g
            result[i * 3 + 2] = b
        return bytes(result)

    def to_rgba(self) -> bytes:
        """Convert to RGBA pixel data (4 bytes per pixel).

        Palette index 0 is treated as transparent.
        """
        indexed = self.to_indexed()
        result = bytearray(len(indexed) * 4)
        for i, idx in enumerate(indexed):
            if idx == 0:
                result[i * 4 : i * 4 + 4] = b"\x00\x00\x00\x00"
            else:
                r, g, b = self.palette[idx] if idx < len(self.palette) else (0, 0, 0)
                result[i * 4] = r
                result[i * 4 + 1] = g
                result[i * 4 + 2] = b
                result[i * 4 + 3] = 255
        return bytes(result)


def _parse_palette(data: bytes, offset: int) -> list[tuple[int, int, int]]:
    """Parse a 32-entry Amiga 12-bit palette."""
    palette = []
    for i in range(32):
        color = struct.unpack_from(">H", data, offset + i * 2)[0]
        r = ((color >> 8) & 0xF) * 17
        g = ((color >> 4) & 0xF) * 17
        b = (color & 0xF) * 17
        palette.append((r, g, b))
    return palette


def parse_sprites(data: bytes) -> list[Sprite]:
    """Parse sprite or icon image data from a bank's raw data.

    Args:
        data: the raw bank data (after magic for bare files, after AmBk header
              for wrapped files). Starts with the u16 image count.

    Returns:
        List of Sprite objects.
    """
    if len(data) < 2:
        raise ValueError(f"Sprite data too short: {len(data)} bytes")

    num_images = struct.unpack_from(">H", data, 0)[0]
    if num_images == 0:
        return []

    # Palette is at the end: 32 entries * 2 bytes = 64 bytes
    palette = _parse_palette(data, len(data) - 64)

    sprites = []
    offset = 2
    for i in range(num_images):
        if offset + 10 > len(data):
            raise ValueError(f"Truncated sprite header at image {i}, offset {offset}")

        w_words, h, num_planes, hx, hy = struct.unpack_from(">HHHHH", data, offset)
        offset += 10

        width = w_words * 16
        plane_size = w_words * 2 * h  # bytes per bitplane
        total_size = plane_size * num_planes

        if offset + total_size > len(data):
            raise ValueError(
                f"Truncated sprite data at image {i}: need {total_size} bytes at offset {offset}, "
                f"but only {len(data) - offset} remain"
            )

        planes = []
        for p in range(num_planes):
            plane_start = offset + p * plane_size
            planes.append(data[plane_start : plane_start + plane_size])
        offset += total_size

        # Mask out flip flags from hotspot_x (bits 14-15)
        hotspot_x = hx & 0x3FFF
        hotspot_y = hy

        sprites.append(
            Sprite(
                width=width,
                height=h,
                num_planes=num_planes,
                hotspot_x=hotspot_x,
                hotspot_y=hotspot_y,
                palette=palette,
                planes=planes,
            )
        )

    return sprites
