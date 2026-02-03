"""
Image dimension helpers - no PIL required.
Parses JPEG/PNG/WebP headers to get width/height from bytes.
"""

import struct
from typing import Optional, Tuple


def get_image_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    """
    Get (width, height) from image bytes. Supports JPEG, PNG, WebP.
    Returns None if format unknown or parse fails.
    """
    if not data or len(data) < 24:
        return None
    # JPEG: SOF0 (0xFFC0) has height, width at offset 5
    if data[:2] == b"\xff\xd8":
        return _jpeg_dimensions(data)
    # PNG: width at 16-19, height at 20-23 (big-endian)
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return _png_dimensions(data)
    # WebP: RIFF....WEBP then VP8/VP8L/VP8X
    if data[:4] == b"RIFF" and len(data) >= 30 and data[8:12] == b"WEBP":
        return _webp_dimensions(data)
    return None


def _jpeg_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    i = 2
    while i < len(data) - 1:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker == 0xC0 or marker == 0xC1 or marker == 0xC2:  # SOF0, SOF1, SOF2
            if i + 9 <= len(data):
                height, width = struct.unpack(">HH", data[i + 5 : i + 9])
                return (width, height)
            return None
        if marker == 0xD8 or marker == 0x01:  # SOI, TEM
            i += 2
            continue
        if i + 4 <= len(data):
            length = struct.unpack(">H", data[i + 2 : i + 4])[0]
            i += 2 + length
        else:
            i += 1
    return None


def _png_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    if len(data) < 24:
        return None
    width, height = struct.unpack(">II", data[16:24])
    return (width, height)


def _webp_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    if len(data) < 30:
        return None
    # VP8 lossy: bytes 26-27 width, 28-29 height (little-endian, 2 less than actual)
    if data[12:16] == b"VP8 ":
        w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return (w, h)
    # VP8L: bytes 21-24 (width 14 bits, height 14 bits in 4 bytes)
    if data[12:16] == b"VP8L" and len(data) >= 25:
        b = data[21:25]
        n = struct.unpack("<I", b)[0]
        w = (n & 0x3FFF) + 1
        h = ((n >> 14) & 0x3FFF) + 1
        return (w, h)
    # VP8X: bytes 24-27 (width-1) 24-bit LE, 28-31 (height-1) 24-bit LE
    if data[12:16] == b"VP8X" and len(data) >= 32:
        w = (struct.unpack("<I", data[24:28])[0] & 0xFFFFFF) + 1
        h = (struct.unpack("<I", data[28:32])[0] & 0xFFFFFF) + 1
        return (w, h)
    return None


# Minimum dimensions for "acceptable" quality (avoid pixelated crop)
MIN_IMAGE_WIDTH = 640
MIN_IMAGE_HEIGHT = 480


def meets_minimum_resolution(data: bytes) -> bool:
    """True if image has at least MIN_IMAGE_WIDTH and MIN_IMAGE_HEIGHT."""
    dims = get_image_dimensions(data)
    if not dims:
        return True  # unknown format: allow (don't block)
    w, h = dims
    return w >= MIN_IMAGE_WIDTH and h >= MIN_IMAGE_HEIGHT
