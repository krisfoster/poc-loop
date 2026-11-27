#!/usr/bin/env python3
"""Time check for /spike-loop:poc-log (docs/prereqs/spec.md, section 3). Standard library, Python 3.9+.

Usage: python3 time_check.py --root <repo root> --docs <poc-spec | .>

Prints two lines and exits 0:
    Elapsed <elapsed> of <timebox as written>, <n> entries.
    timebox: over | within | unknown
On a missing file or a missing Started: date, prints one "time check: <reason>" line, naming the file
relative to the repo root, and exits 3. Reads <docs>/POC.md and <docs>/LOG.md only, writes nothing.
--now "YYYY-MM-DD HH:MM" replaces the clock, for tests.
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

STARTED_RE = re.compile(r"^Started:\s*(\d{4}-\d{2}-\d{2})(?:[ T](\d{1,2}):(\d{2}))?")
TIMEBOX_RE = re.compile(r"\|\s*Timebox[^:|]*:\s*([^|]*?)\s*(?:\||$)")
ENTRY_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})(?: (\d{1,2}):(\d{2}))?(?:\s|$)")
PART_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(minutes?|mins?|m|hours?|hrs?|h|days?|d)\b", re.I)
SEPARATORS_RE = re.compile(r"(?:\s|,|\+|\band\b)*", re.I)
UNIT_MINUTES = {"m": 1, "h": 60, "d": 1440}


class Stop(Exception):
    pass


def parse_timebox(text):
    """Minutes, or None unless the text is one or more number-and-unit parts joined by spaces,
    commas, '+' or 'and'."""
    t = text.strip()
    parts = PART_RE.findall(t)
    if not parts or not SEPARATORS_RE.fullmatch(PART_RE.sub(" ", t)):
        return None
    return sum(float(num) * UNIT_MINUTES[unit[0].lower()] for num, unit in parts)


def entries_of(log):
    """(date, hour, minute) for each dated entry heading outside code fences."""
    out, fenced = [], False
    for line in log.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        m = None if fenced else ENTRY_RE.match(line)
        if m:
            out.append(m.groups())
    return out


def at(day, hour, minute):
    return datetime.datetime.strptime("%s %02d:%s" % (day, int(hour), minute), "%Y-%m-%d %H:%M")


def elapsed_text(minutes):
    minutes = max(0, int(minutes))
    h, m = divmod(minutes, 60)
    return "%dh %dm" % (h, m) if h else "%dm" % m


def check(root, docs, now):
    rel = (lambda name: name) if docs in (".", "") else (lambda name: "%s/%s" % (docs, name))
    base = Path(root) if docs in (".", "") else Path(root) / docs
    texts = {}
    for name in ("POC.md", "LOG.md"):
        p = base / name
        if not p.is_file():
            raise Stop("%s is missing" % rel(name))
        try:
            texts[name] = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            raise Stop("%s cannot be read" % rel(name))
    header = next((l.strip() for l in texts["POC.md"].splitlines() if l.strip().startswith("Started:")), "")
    started = STARTED_RE.match(header)
    if not started:
        raise Stop("no Started: date in %s" % rel("POC.md"))
    entries = entries_of(texts["LOG.md"])
    day, hour, minute = started.groups()
    try:
        if hour is not None:
            start = at(day, hour, minute)
        else:
            start = at(day, 0, "00")
            for e_day, e_hour, e_min in entries:
                if e_day == day and e_hour is not None:
                    try:
                        start = at(e_day, e_hour, e_min)
                        break
                    except ValueError:
                        continue
    except ValueError:
        raise Stop("the Started: date in %s is not a valid date and time" % rel("POC.md"))
    box_match = TIMEBOX_RE.search(header)
    box_text = box_match.group(1) if box_match else ""
    box = parse_timebox(box_text)
    minutes = (now - start).total_seconds() / 60
    if minutes < 0:
        state = "unknown"
    elif box is None:
        state = "unknown"
    else:
        state = "over" if minutes > box else "within"
    n = len(entries)
    line = "Elapsed %s of %s, %d %s." % (elapsed_text(minutes), box_text or "no timebox", n, "entry" if n == 1 else "entries")
    return line, state


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", required=True)
    ap.add_argument("--docs", required=True)
    ap.add_argument("--now", help=argparse.SUPPRESS)
    a = ap.parse_args(argv)
    try:
        now = datetime.datetime.strptime(a.now, "%Y-%m-%d %H:%M") if a.now else datetime.datetime.now()
    except ValueError:
        print("time check: --now is not a valid date and time")
        return 3
    try:
        line, state = check(a.root, a.docs, now)
    except Stop as exc:
        print("time check: %s" % exc)
        return 3
    print(line)
    print("timebox: %s" % state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
