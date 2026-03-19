"""Shared Amiga planar bitmap conversion utilities."""

from __future__ import annotations


def planar_to_indexed(planes: list[bytes], width: int, height: int) -> bytes:
    """Convert planar bitplane data to chunky indexed pixels.

    Args:
        planes: list of bytearrays/bytes, one per bitplane.
        width: image width in pixels.
        height: image height in pixels.

    Returns:
        One byte per pixel, each byte being a palette index.
    """
    width_bytes = (width + 7) // 8
    num_planes = len(planes)
    result = bytearray(width * height)

    for y in range(height):
        for x in range(width):
            byte_idx = y * width_bytes + x // 8
            bit = 7 - (x % 8)
            index = 0
            for plane_num in range(num_planes):
                if planes[plane_num][byte_idx] & (1 << bit):
                    index |= 1 << plane_num
            result[y * width + x] = index

    return bytes(result)


def indexed_to_rgb(indexed: bytes, palette: list[tuple[int, int, int]]) -> bytes:
    """Convert indexed pixel data to RGB (3 bytes per pixel)."""
    result = bytearray(len(indexed) * 3)
    for i, idx in enumerate(indexed):
        r, g, b = palette[idx] if idx < len(palette) else (0, 0, 0)
        result[i * 3] = r
        result[i * 3 + 1] = g
        result[i * 3 + 2] = b
    return bytes(result)


def indexed_to_rgba(indexed: bytes, palette: list[tuple[int, int, int]]) -> bytes:
    """Convert indexed pixel data to RGBA (4 bytes per pixel).

    Palette index 0 is treated as transparent.
    """
    result = bytearray(len(indexed) * 4)
    for i, idx in enumerate(indexed):
        if idx == 0:
            result[i * 4 : i * 4 + 4] = b"\x00\x00\x00\x00"
        else:
            r, g, b = palette[idx] if idx < len(palette) else (0, 0, 0)
            result[i * 4] = r
            result[i * 4 + 1] = g
            result[i * 4 + 2] = b
            result[i * 4 + 3] = 255
    return bytes(result)
