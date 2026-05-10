#!/usr/bin/env python3
"""
Recursively scans a directory for .txt files encoded in GBK (or GB2312/GB18030),
converts them to UTF-8 in-place (no backup kept), and reports results.

Usage:
    python convert_gbk_to_utf8.py /path/to/directory
"""

import sys
import os
import chardet

# GBK encoding aliases chardet may return
GBK_VARIANTS = {"gbk", "gb2312", "gb18030", "gb-18030"}

# Chardet sometimes under-detects; escalate through this chain on decode failure
GBK_FALLBACK_CHAIN = ["gbk", "gb18030"]


def detect_encoding(filepath: str) -> str | None:
    """Return the detected encoding name (lowercase), or None on failure."""
    with open(filepath, "rb") as f:
        raw = f.read()
    if not raw:
        return None
    result = chardet.detect(raw)
    encoding = result.get("encoding")
    return encoding.lower() if encoding else None


def read_with_fallback(filepath: str, detected: str) -> tuple[str, str]:
    """
    Try to read the file with the detected encoding.
    If it fails, escalate through GBK_FALLBACK_CHAIN.
    Returns (content, encoding_used) or raises UnicodeDecodeError.
    """
    candidates = [detected] + [e for e in GBK_FALLBACK_CHAIN if e != detected]
    for enc in candidates:
        try:
            with open(filepath, "r", encoding=enc, errors="strict") as f:
                return f.read(), enc
        except (UnicodeDecodeError, LookupError):
            continue
    raise UnicodeDecodeError(detected, b"", 0, 1, "All GBK-family encodings failed")


def convert_file(filepath: str) -> tuple[bool, str]:
    """
    Read the file with its detected encoding, write it back as clean UTF-8.
    - GBK/GB2312/GB18030 files are decoded and re-saved as UTF-8.
    - UTF-8-SIG (UTF-8 with BOM) files are re-saved as clean UTF-8 (BOM stripped).
    - All other encodings are skipped.
    Returns (success: bool, message: str).
    """
    encoding = detect_encoding(filepath)

    if encoding is None:
        return False, "Could not detect encoding (empty or binary?)"

    # Handle UTF-8 with BOM — strip the BOM, save as clean UTF-8
    if encoding == "utf-8-sig":
        try:
            with open(filepath, "r", encoding="utf-8-sig") as f:
                content = f.read()
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            return True, "BOM stripped (utf-8-sig → utf-8)"
        except OSError as e:
            return False, f"Write error: {e}"

    if encoding not in GBK_VARIANTS:
        return False, f"Skipped — detected encoding: {encoding}"

    try:
        content, used_enc = read_with_fallback(filepath, encoding)
    except UnicodeDecodeError as e:
        return False, f"Read error — all GBK-family encodings failed: {e}"

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        return False, f"Write error: {e}"

    note = f" (escalated from {encoding})" if used_enc != encoding else ""
    return True, f"Converted ({used_enc}{note} → utf-8)"


def scan_and_convert(root_dir: str) -> None:
    if not os.path.isdir(root_dir):
        print(f"Error: '{root_dir}' is not a valid directory.")
        sys.exit(1)

    converted, skipped, failed = 0, 0, 0

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if not filename.lower().endswith(".txt"):
                continue

            filepath = os.path.join(dirpath, filename)
            success, message = convert_file(filepath)

            status = "✓" if success else ("✗" if "error" in message.lower() else "–")
            print(f"  {status}  {filepath}\n     └─ {message}\n")

            if success:
                converted += 1
            elif "Skipped" in message:
                skipped += 1
            else:
                failed += 1

    print("─" * 60)
    print(f"  Done. Converted: {converted}  |  Skipped: {skipped}  |  Failed: {failed}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python convert_gbk_to_utf8.py /path/to/directory")
        sys.exit(1)

    scan_and_convert(sys.argv[1])
