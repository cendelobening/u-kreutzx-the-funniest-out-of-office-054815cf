"""Out-of-office auto-reply entry.

Writes a single funny out-of-office line to entry.txt in the output
directory, with no trailing newline, using only the standard library.
"""

import os
import stat
import sys
import tempfile

LINE = "I'm out of office \u2014 my inbox went on vacation too, and it's ignoring you even better than I ever could. Back Monday, probably."

OUTPUT_FILENAME = "entry.txt"
MAX_CHARS = 140


def validate(line):
    """Check the entry line meets the bounty gate before writing it."""
    if not isinstance(line, str):
        raise ValueError("entry line must be a string")
    if not 1 <= len(line) <= MAX_CHARS:
        raise ValueError("entry line must be 1 to 140 characters, got %d" % len(line))
    if "\n" in line or "\r" in line:
        raise ValueError("entry line must be a single line")
    if line != line.strip():
        raise ValueError("entry line must not have leading or trailing whitespace")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in line):
        raise ValueError("entry line must not contain control characters")
    if not any(ch.isalpha() for ch in line):
        raise ValueError("entry line must contain at least one letter")


def write_entry(line, output_dir):
    """Write the line atomically and verify what landed on disk."""
    validate(line)
    os.makedirs(output_dir, exist_ok=True)

    data = line.encode("utf-8")
    target = os.path.join(output_dir, OUTPUT_FILENAME)
    if os.path.isdir(target):
        raise RuntimeError("output path %s is a directory" % target)

    fd, tmp_path = tempfile.mkstemp(prefix=".entry-", dir=output_dir)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp_path, target)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    os.chmod(target, 0o644)

    with open(target, "rb") as handle:
        written = handle.read()
    if written != data:
        raise RuntimeError("verification failed: bytes on disk differ from the entry line")
    if written.decode("utf-8") != line:
        raise RuntimeError("verification failed: file does not decode to the entry line")
    if written.endswith(b"\n"):
        raise RuntimeError("verification failed: file has a trailing newline")
    mode = stat.S_IMODE(os.stat(target).st_mode)
    if mode != 0o644:
        raise RuntimeError("verification failed: mode is %o, expected 644" % mode)

    return len(line), len(data)


def main():
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    try:
        chars, nbytes = write_entry(LINE, output_dir)
    except (ValueError, OSError, RuntimeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print("wrote %d characters (%d bytes) to entry.txt" % (chars, nbytes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
