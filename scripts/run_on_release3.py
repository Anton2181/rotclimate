"""Run an existing builder unchanged on the release-3 towns.

    run_on_release3.py <script.py> ['OLD=>NEW' ...] [-- script args]

Installs polity.release3_placement, then executes the script's own source with
the given literal replacements (each must occur exactly once), typically to
redirect its output folder. The original script file is never modified.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]

if __name__ == '__main__':
    args = sys.argv[1:]; rest = []
    if '--' in args:
        rest = args[args.index('--') + 1:]; args = args[:args.index('--')]
    script = (ROOT / args[0]).resolve(); source = script.read_text()
    for pair in args[1:]:
        old, new = pair.split('=>', 1)
        if source.count(old) != 1:
            raise ValueError(f'Expected exactly one occurrence of {old!r} in {script.name}, found {source.count(old)}')
        source = source.replace(old, new)
    from polity.release3_placement import install
    used = install(); sys.argv = [str(script)] + rest
    exec(compile(source, str(script), 'exec'), {'__name__': '__main__', '__file__': str(script)})
    print('release-3 placements used:', used)
