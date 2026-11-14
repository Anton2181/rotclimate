"""Run an existing script unchanged except for literal path/key replacements (each must occur at least once).

    exec_with.py <script.py> ['OLD=>NEW' ...] [-- script args]

Like run_on_release3.py but without installing the release-3 placement hook. The script file is never modified."""
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
        if source.count(old) < 1: raise ValueError(f'{old!r} does not occur in {script.name}')
        source = source.replace(old, new)
    sys.argv = [str(script)] + rest
    exec(compile(source, str(script), 'exec'), {'__name__': '__main__', '__file__': str(script)})
