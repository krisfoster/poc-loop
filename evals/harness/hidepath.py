"""Build a PATH that hides some tools: a directory of symlinks to every executable on the given PATH,
first occurrence wins, leaving out names that match a hide pattern. Used by the eval runner's
hide_tools case field and by the prerequisite checker tests. Standard library only."""
import fnmatch
import os

ALIASES = {"python3": ["python3", "python3.*", "python", "python[0-9]*"]}


def patterns(tools):
    out = []
    for t in tools:
        out += ALIASES.get(t, [t])
    return out


def hidden_path(dest, hide, path=None):
    """Fill dest (created) with symlinks and return it as a one-entry PATH string."""
    os.makedirs(dest)
    pats, seen = patterns(hide), set()
    for d in (path if path is not None else os.environ.get("PATH", "")).split(os.pathsep):
        if not d or not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if name in seen or os.path.isdir(p) or not os.access(p, os.X_OK):
                continue
            seen.add(name)
            if not any(fnmatch.fnmatch(name, h) for h in pats):
                os.symlink(p, os.path.join(dest, name))
    return dest
