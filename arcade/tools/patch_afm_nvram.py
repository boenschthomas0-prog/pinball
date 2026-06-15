#!/usr/bin/env python3
"""
patch_afm_nvram.py — Patch a PinMAME `afm_113b.nv` to a deterministic pristine
state and recompute the WPC checksums so the ROM accepts the file on boot.

Map source: github.com/tomlogic/pinmame-nvram-maps  (commit 90186be58b…)
File:       maps/williams/wpc/afm_113.map.json
Platform:   williams-wpc-12K  (NVRAM at 0x0000, size 0x3000 = 12288 bytes;
                               PinMAME appends a 46-byte footer → file = 12334)

Checksum algorithms (verified by recomputing every checksum16 span against the
current live file — all 15 spans matched):

  * 16-bit (most groups): span [start..end] *includes* its own 2-byte checksum
    at [end-1, end]. Stored MSB-first. Value = (0xFFFF - sum(data[start..end-2])) & 0xFFFF.

  * 8-bit (Audits, span 6161..7036, grouping 6): every 6-byte group consists of
    5 data bytes + 1 trailing checksum byte. Value = (0xFF - sum(5 data)) & 0xFF.

What this tool changes:

  * Credits counter (7490..7497) → 0  (clean coin chute on boot)
  * Free Play (7192)             → 0  (kept OFF, user wants coin-insert)
  * Match Feature %  (7099)      → 0  (=OFF, no MATCH cycle at end of game)
  * Replay L1..L4  (7079..7086)  → 0  (all replay levels OFF → no replay award)
  * Replay Levels  (7077)        → 1
  * Last-game leftovers          → reset to zero:
      - player_count (5905)
      - Player 1..4 scores (5792, 5799, 5806, 5813; 6 BCD bytes each)
      - current_player (949), current_ball (950), extra_balls (951),
        eb_on_this_ball (952), game_over (135)

What this tool does NOT change (and why):

  * Coin-slot UNITS / Pricing Style adjustments are NOT exposed in the public
    tomlogic afm_113.map.json (the map only covers A.1 Standard Adjustments,
    not A.2 Pricing). The factory default for afm_113 is already "USA 1"
    (1 coin = 1 credit on the centre slot). If the live NVRAM ever drifts from
    USA-1, that has to be set from the operator menu — not safe to guess offsets.

# ---------------------------------------------------------------------------
# TODO: A.2 Pricing Adjustments — research log (2026-05-27)
# ---------------------------------------------------------------------------
# Goal was "1 Coin = 1 Credit for all four coin slots, no Free Play".
# Result: ABORTED — could not verify offsets from any authoritative source.
#
# Sources checked:
#   * https://raw.githubusercontent.com/vpinball/pinmame/master/src/wpc/wpc.c
#     -> no adjustment/coin/pricing references (PinMAME treats NVRAM as an
#        opaque blob; the WPC ROM owns the NVRAM layout).
#   * https://raw.githubusercontent.com/vpinball/pinmame/master/src/wpc/core.c
#     -> only generic core_nvram() RAM read/write helper, no offsets.
#   * https://raw.githubusercontent.com/vpinball/pinmame/master/src/wpc/sims/wpc/full/afm.c
#     -> AFM "sim" only wires switches/coils, contains no NVRAM offsets.
#   * https://github.com/tomlogic/pinmame-nvram-maps (main branch, ~110 maps)
#     -> Surveyed mm_109, mm_10, cv_14, cv_20h, congo_21, nf_23, ngg_13, jy_12,
#        corv_21, i500_11r — every WPC-95 map documents only `free_play`; none
#        documents A.2 Pricing (coin-slot units / units-per-credit / pricing
#        style). The tomlogic project explicitly stops at A.1 Standard
#        Adjustments for WPC.
#   * https://github.com/francisdb/pinmame-nvram (afm_113b.nv test fixture)
#     -> Parsed JSON only mirrors tomlogic, no additional fields.
#   * https://github.com/syd711/nvrams/blob/main/afm_113b.nv/afm_113b.nv
#     -> Compared byte-for-byte against our live NVRAM. Only 16 bytes differ
#        and ALL are in already-mapped regions (credits @ 7490-99, replay
#        levels @ 7077-80, scores @ 5792-5817, current player @ 949-50,
#        player count @ 5905, Adjustments checksum @ 7331-32). No diffs in
#        the suspected pricing range 7131..7189 — useless as a probe.
#   * https://bitbucket.org/sbe/pinmame-nvram-maps -> 404 (auth-walled).
#
# Circumstantial evidence (UNVERIFIED — do NOT write to these):
#   buf[7182]=0x19 (25), buf[7184]=0x64 (100), buf[7186]=0x19 (25),
#   buf[7188]=0x64 (100). This matches the WPC manual's "USA 1" coin-slot
#   value defaults (25c/100c/25c/100c). The 1-byte 0x00 gaps at 7181/7183/
#   7185/7187 look like big-endian high bytes of 16-bit slot units. But:
#   without ROM disassembly or a trusted map this is a guess. Per project
#   policy ("never guess NVRAM offsets") we refuse to write here.
#
# Current state of our live NVRAM (confirmed from byte dump):
#   * Free Play (7192)      = 0   (OFF)            <- already correct
#   * Max Credits (7190)    = 10                    <- factory default
#   * Likely Slot units     = 25/100/25/100 cents   <- "USA 1" preset
#   With "USA 1", inserting one coin in the CENTRE chute (slot 2 = 100c, the
#   primary chute) already buys exactly one credit. Left/right side slots
#   (25c) accumulate units until 100 is reached, then issue a credit. This
#   is the standard arcade-cabinet behaviour and matches what most VPX users
#   want for free-coin play with the "5" key (which fires coin slot 2).
#
# Recommended next steps if "1 unit per slot, 1 unit per credit" really is
# required (e.g. for left-flipper-side service button workflows):
#   (a) Boot afm_113b in PinMAME with operator menu (-extra_options) and use
#       A.2.01..A.2.07 to set "Custom Pricing" + units=1 for all slots, save,
#       diff the resulting NVRAM against the pre-state. The diff bytes ARE
#       the offsets. That gives a *verified* map without guessing.
#   (b) Find a WPC ROM disassembly that names the adjustment RAM block
#       (e.g. freewpc source — but freewpc is a homebrew OS, not afm_113b).
#
# Until one of (a)/(b) is done, this tool intentionally does NOT touch the
# pricing block. The cabinet still accepts coins via the centre slot.
# ---------------------------------------------------------------------------

Usage:
    patch_afm_nvram.py <input.nv> <output.nv> [--map afm_113.map.json] [--verify]

Idempotent: running it twice on its own output produces an identical file.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

NVRAM_SIZE = 0x3000           # 12288, declared by platform williams-wpc-12K
EXPECTED_FILE_SIZE = 12334    # NVRAM + 46-byte PinMAME footer

# ---------------------------------------------------------------------------
# Checksum helpers
# ---------------------------------------------------------------------------

def wpc_checksum16(buf: bytearray, start: int, end: int) -> None:
    """Recompute a WPC 16-bit checksum.

    The checksum lives in the last two bytes of the [start..end] span,
    big-endian. The data covered is bytes [start..end-2].

        ck = (0xFFFF - sum(data)) & 0xFFFF
    """
    s = sum(buf[start:end - 1]) & 0xFFFF
    ck = (0xFFFF - s) & 0xFFFF
    buf[end - 1] = (ck >> 8) & 0xFF
    buf[end]     = ck & 0xFF


def wpc_checksum8_groups(buf: bytearray, start: int, end: int, group: int) -> None:
    """Recompute the per-group 8-bit Audits checksum.

    Each `group` bytes consist of (group-1) data bytes followed by a single
    checksum byte = (0xFF - sum(data)) & 0xFF.
    """
    total = end - start + 1
    if total % group != 0:
        raise ValueError(f"checksum8 span {start}..{end} not divisible by group {group}")
    for base in range(start, end + 1, group):
        s = sum(buf[base:base + group - 1]) & 0xFF
        buf[base + group - 1] = (0xFF - s) & 0xFF


# ---------------------------------------------------------------------------
# Patches
# ---------------------------------------------------------------------------

def zero_bytes(buf: bytearray, offset: int, length: int = 1) -> None:
    for i in range(length):
        buf[offset + i] = 0


def patch(buf: bytearray) -> dict:
    """Apply all pristine patches. Returns a before/after dict for the report."""
    before: dict[str, bytes] = {}
    after:  dict[str, bytes] = {}

    targets = [
        # label,                       offset, length
        ("Credits (1+6 bytes)",        7490,   8),
        ("Free Play (bool)",           7192,   1),
        ("Match Feature %",            7099,   1),
        ("Replay Levels count",        7077,   1),
        ("Replay L1 (bcd)",            7079,   2),
        ("Replay L2 (bcd)",            7081,   2),
        ("Replay L3 (bcd)",            7083,   2),
        ("Replay L4 (bcd)",            7085,   2),
        ("Player count",               5905,   1),
        ("Player 1 score (bcd)",       5792,   6),
        ("Player 2 score (bcd)",       5799,   6),
        ("Player 3 score (bcd)",       5806,   6),
        ("Player 4 score (bcd)",       5813,   6),
        ("Current player",             949,    1),
        ("Current ball",               950,    1),
        ("Extra balls",                951,    1),
        ("EBs this ball",              952,    1),
        ("Game-over flag",             135,    1),
    ]

    for label, off, n in targets:
        before[label] = bytes(buf[off:off + n])
        zero_bytes(buf, off, n)
        # Special-case: Replay Levels = 1 (at least one slot must exist even
        # when all four thresholds are 0; the ROM ignores them as OFF then).
        if label == "Replay Levels count":
            buf[off] = 1
        after[label] = bytes(buf[off:off + n])

    return {"before": before, "after": after}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def load_map(map_path: Path) -> dict:
    with map_path.open() as f:
        return json.load(f)


def recompute_all_checksums(buf: bytearray, mapping: dict) -> None:
    for c in mapping.get("checksum16", []):
        wpc_checksum16(buf, c["start"], c["end"])
    for c in mapping.get("checksum8", []):
        wpc_checksum8_groups(buf, c["start"], c["end"], c.get("groupings", 1))


def verify_all_checksums(buf: bytearray, mapping: dict) -> list[str]:
    errors: list[str] = []
    for c in mapping.get("checksum16", []):
        start, end = c["start"], c["end"]
        s = sum(buf[start:end - 1]) & 0xFFFF
        expected = (0xFFFF - s) & 0xFFFF
        stored = (buf[end - 1] << 8) | buf[end]
        if expected != stored:
            errors.append(
                f"checksum16 span {start}..{end} mismatch: expected {expected:#06x} stored {stored:#06x}"
            )
    for c in mapping.get("checksum8", []):
        start, end, group = c["start"], c["end"], c.get("groupings", 1)
        for base in range(start, end + 1, group):
            s = sum(buf[base:base + group - 1]) & 0xFF
            expected = (0xFF - s) & 0xFF
            stored = buf[base + group - 1]
            if expected != stored:
                errors.append(
                    f"checksum8 group @{base} mismatch: expected {expected:#04x} stored {stored:#04x}"
                )
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path, help="source .nv file")
    ap.add_argument("output", type=Path, help="destination .nv file")
    ap.add_argument("--map", type=Path,
                    default=Path("/tmp/afm_113.map.json"),
                    help="path to afm_113.map.json")
    ap.add_argument("--verify-only", action="store_true",
                    help="don't patch — just verify checksums against the file")
    args = ap.parse_args()

    if not args.input.exists():
        print(f"error: {args.input} does not exist", file=sys.stderr)
        return 2
    if not args.map.exists():
        print(f"error: map file {args.map} not found", file=sys.stderr)
        return 2

    data = bytearray(args.input.read_bytes())
    if len(data) != EXPECTED_FILE_SIZE:
        print(f"warning: file size {len(data)} != expected {EXPECTED_FILE_SIZE}", file=sys.stderr)

    mapping = load_map(args.map)
    meta = mapping.get("_metadata", {})
    if "afm_113b" not in meta.get("roms", []) and "afm_113" not in meta.get("roms", []):
        print(f"error: map does not cover afm_113b (roms={meta.get('roms')})", file=sys.stderr)
        return 2

    if args.verify_only:
        errors = verify_all_checksums(data, mapping)
        if errors:
            for e in errors:
                print("  " + e)
            print(f"FAIL: {len(errors)} checksum errors")
            return 1
        print("OK: all checksums valid")
        return 0

    report = patch(data)
    recompute_all_checksums(data, mapping)

    errors = verify_all_checksums(data, mapping)
    if errors:
        print("error: checksums still bad after recompute:", file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)
        return 3

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(bytes(data))

    print(f"wrote {args.output}  ({len(data)} bytes)")
    print()
    print("--- patches applied (offset: before -> after) ---")
    before_map = report["before"]
    after_map  = report["after"]
    for label in before_map:
        b = before_map[label].hex()
        a = after_map[label].hex()
        marker = "" if b != a else "  (no change)"
        print(f"  {label:<30s} {b}  ->  {a}{marker}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
