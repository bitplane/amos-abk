from __future__ import annotations

import struct
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

# Magic bytes for supported bank types
MAGIC_AMBK = b"AmBk"
MAGIC_AMSP = b"AmSp"
MAGIC_AMIC = b"AmIc"

# Known but unsupported magic bytes
MAGIC_AMBS = b"AmBs"
MAGIC_CRM2 = b"CrM2"
MAGIC_IMP = b"IMP!"
MAGIC_PPBK = b"PPbk"

# Conventional bank numbers for bare sprite/icon files
SPRITE_BANK_NUMBER = 1
ICON_BANK_NUMBER = 2

# AmBk header: magic(4) + bank_num(2) + mem_type(2) + length(4) + name(8) = 20
AMBK_HEADER_SIZE = 20
# The length field counts from byte 12 onward (name + data), so
# the fixed prefix not counted is magic(4) + bank_num(2) + mem_type(2) + length(4) = 12
AMBK_PREFIX_SIZE = 12

LENGTH_MASK = 0x0FFFFFFF
FLAGS_MASK = 0xF0000000


@dataclass
class DataBank:
    """A single AMOS memory bank."""

    number: int
    name: str
    memory_type: int
    flags: int
    data: bytes


class AbkFile:
    """An AMOS bank file containing one or more banks."""

    def __init__(self, banks: list[DataBank]):
        self.banks = banks

    def __repr__(self) -> str:
        bank_names = ", ".join(b.name for b in self.banks)
        return f"AbkFile([{bank_names}])"


def _read_ambk_bank(stream: BytesIO) -> DataBank:
    """Read a single AmBk-wrapped bank from the stream."""
    header = stream.read(AMBK_HEADER_SIZE)
    if len(header) < AMBK_HEADER_SIZE:
        raise ValueError(f"Truncated AmBk header: expected {AMBK_HEADER_SIZE} bytes, got {len(header)}")

    magic = header[0:4]
    if magic != MAGIC_AMBK:
        raise ValueError(f"Expected AmBk magic, got {magic!r}")

    bank_num, mem_type, length_raw = struct.unpack_from(">HHI", header, 4)
    name = header[12:20].decode("ascii", errors="replace").rstrip()

    flags = length_raw & FLAGS_MASK
    data_length = (length_raw & LENGTH_MASK) - 8  # subtract name field (8 bytes)

    if data_length < 0:
        raise ValueError(f"Invalid bank length: {length_raw:#x} (data_length={data_length})")

    data = stream.read(data_length)
    if len(data) < data_length:
        raise ValueError(f"Truncated bank data for '{name}': expected {data_length} bytes, got {len(data)}")

    return DataBank(
        number=bank_num,
        name=name,
        memory_type=mem_type,
        flags=flags,
        data=data,
    )


def _read_bare_bank(stream: BytesIO, magic: bytes) -> DataBank:
    """Read a bare AmSp or AmIc bank (no AmBk wrapper)."""
    data = stream.read()

    if magic == MAGIC_AMSP:
        return DataBank(number=SPRITE_BANK_NUMBER, name="Sprites", memory_type=0, flags=0, data=data)

    return DataBank(number=ICON_BANK_NUMBER, name="Icons", memory_type=0, flags=0, data=data)


def load(source: str | Path | BytesIO) -> AbkFile:
    """Load an AMOS bank file.

    Args:
        source: file path (str or Path) or a readable BytesIO stream.

    Returns:
        An AbkFile containing the parsed banks.
    """
    if isinstance(source, (str, Path)):
        with open(source, "rb") as f:
            return _load_stream(BytesIO(f.read()))

    return _load_stream(source)


def _load_stream(stream: BytesIO) -> AbkFile:
    """Parse banks from a byte stream."""
    magic = stream.read(4)
    if len(magic) < 4:
        raise ValueError(f"File too short: expected at least 4 bytes, got {len(magic)}")

    if magic in (MAGIC_AMBS, MAGIC_CRM2, MAGIC_IMP, MAGIC_PPBK):
        kind = magic.decode("ascii", errors="replace")
        raise ValueError(f"Unsupported format: {kind} (not a bank file)")

    if magic in (MAGIC_AMSP, MAGIC_AMIC):
        bank = _read_bare_bank(stream, magic)
        return AbkFile([bank])

    if magic == MAGIC_AMBK:
        stream.seek(0)
        banks = []
        while True:
            banks.append(_read_ambk_bank(stream))
            next_magic = stream.read(4)
            if len(next_magic) < 4:
                break
            if next_magic != MAGIC_AMBK:
                raise ValueError(f"Expected AmBk magic at offset {stream.tell() - 4}, got {next_magic!r}")
            stream.seek(stream.tell() - 4)
        return AbkFile(banks)

    raise ValueError(f"Unknown magic: {magic!r}")
