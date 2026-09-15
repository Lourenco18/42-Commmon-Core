#!/usr/bin/env python3
"""raw_helpers.py - tiny helper used by tests/integration_test.sh to build
and verify the --raw binary wire format (subject VIII.2) without needing
to hand-write binary data in bash.

Usage:
    raw_helpers.py produce <client_bin> <ipc_id> <topic> key:value [key:value ...]
        Encodes each key:value pair as a raw producer record and pipes it
        into `<client_bin> <ipc_id> produce <topic> --raw`.

    raw_helpers.py check <captured_output_file> offset:key:value [...]
        Parses a captured raw *consumer* output file (which starts with the
        plain-text "subscribed to <topic>\n" confirmation line, followed by
        the binary stream) and checks it matches the expected
        offset:key:value records, in order. Prints nothing on success,
        exits 0; prints a diff-ish message and exits 1 on mismatch.
"""
import struct
import subprocess
import sys


def encode_record(key: str, value: str) -> bytes:
    k = key.encode()
    v = value.encode()
    return struct.pack("<I", len(k)) + k + struct.pack("<I", len(v)) + v


def cmd_produce(argv):
    client_bin, ipc_id, topic, *pairs = argv
    payload = b"".join(encode_record(*p.split(":", 1)) for p in pairs)
    proc = subprocess.run([client_bin, ipc_id, "produce", topic, "--raw"], input=payload)
    sys.exit(proc.returncode)


def parse_stream(data: bytes):
    records = []
    i = 0
    while i + 4 <= len(data):
        offset = struct.unpack_from("<I", data, i)[0]
        i += 4
        if offset == 0xFFFFFFFF:
            break
        keysize = struct.unpack_from("<I", data, i)[0]
        i += 4
        key = data[i:i + keysize].decode()
        i += keysize
        valsize = struct.unpack_from("<I", data, i)[0]
        i += 4
        value = data[i:i + valsize].decode()
        i += valsize
        records.append((offset, key, value))
    return records


def cmd_check(argv):
    path, *expected_specs = argv
    raw = open(path, "rb").read()
    nl = raw.find(b"\n")
    if nl == -1:
        print("no confirmation line found")
        sys.exit(1)
    binary = raw[nl + 1:]
    got = parse_stream(binary)
    expected = []
    for spec in expected_specs:
        offset_s, key, value = spec.split(":", 2)
        expected.append((int(offset_s), key, value))
    if got != expected:
        print(f"expected {expected}, got {got}")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    action, rest = sys.argv[1], sys.argv[2:]
    if action == "produce":
        cmd_produce(rest)
    elif action == "check":
        cmd_check(rest)
    else:
        print(__doc__)
        sys.exit(2)
