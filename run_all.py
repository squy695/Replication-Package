# -*- coding: utf-8 -*-
# Run the scripts of this replication package (figures and tables) and report what they wrote.
import argparse
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {'__pycache__', 'artifact'}
# Leftovers that running the scripts (or an editor) leaves behind.
JUNK_DIRS = {'__pycache__', '.pytest_cache', '.ipynb_checkpoints', '.vscode', '.idea'}
JUNK_EXT = ('.pyc', '.pyo', '.pyw', '.orig', '.bak', '.rej', '~')
JUNK_NAMES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}
SAVE_RE = re.compile(r'\b(?:fig|plt|fig\d*)\.savefig\(')
WRITE_RE = re.compile(r'\.to_csv\(|json\.dump\(|open\([^)]*[\'"][wa][\'"]\)')
OUT_EXT = ('.pdf', '.png', '.csv')

# Plotting scripts backing the paper's figures. Figures that are not data-driven
# (the schematic drawings of Fig. 1/2/6 and the analytic curve of Fig. 12) are not
# part of this package.
PAPER_FIGURES = [
    r'fig 3\fig_3a.py', r'fig 3\fig_3b.py', r'fig 3\fig_3c.py',    # Fig 3a-b-c
    r'fig 4\fig_4a.py', r'fig 4\fig_4b.py', r'fig 4\fig_4c.py',    # Fig 4a-b-c
    r'fig 5\fig_5.py',                                             # Fig 5
    r'fig 7\fig_7a.py', r'fig 7\fig_7b.py',                        # Fig 7a-b
    r'fig 8\fig_8.py',                                             # Fig 8
    r'fig 9\fig_9.py',                                             # Fig 9
    r'fig 10\fig_10.py',                                           # Fig 10
    r'fig 11\fig_11.py',                                           # Fig 11
    r'fig 13\fig_13.py',                                           # Fig 13
]


# Sort key that keeps "fig 2" before "fig 10".
def _natsort(path):
    rel = os.path.relpath(path, HERE)
    m = re.match(r'(fig|table) (\d+)', rel)
    return (0, int(m.group(2)), rel) if m else (1, 0, rel)


# Plotting scripts call savefig; table/helper scripts write a CSV. Anything else
# (this file and the shared helper modules) is not meant to be run on its own.
def discover():
    plots, tables = [], []
    for root, dirs, files in os.walk(HERE):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            if not name.endswith('.py') or name == os.path.basename(__file__):
                continue
            path = os.path.join(root, name)
            try:
                src = open(path, encoding='utf-8').read()
            except (OSError, UnicodeDecodeError):
                continue
            if SAVE_RE.search(src):
                plots.append(path)
            elif WRITE_RE.search(src):
                tables.append(path)
    return sorted(plots, key=_natsort), sorted(tables, key=_natsort)


# Modification time of every figure/table file in the package.
def snapshot():
    state = {}
    for root, dirs, files in os.walk(HERE):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if name.lower().endswith(OUT_EXT):
                path = os.path.join(root, name)
                try:
                    state[path] = os.path.getmtime(path)
                except OSError:
                    pass
    return state


# Delete caches and editor leftovers inside the package; returns what was removed.
def clean():
    removed = []
    for root, dirs, files in os.walk(HERE, topdown=True):
        for name in list(dirs):
            if name not in JUNK_DIRS:
                continue
            path = os.path.join(root, name)
            dirs.remove(name)
            try:
                shutil.rmtree(path)
                removed.append(os.path.relpath(path, HERE) + os.sep)
            except OSError as exc:
                print('  ! cannot remove %s: %s' % (os.path.relpath(path, HERE), exc))
        for name in files:
            if name in JUNK_NAMES or name.lower().endswith(JUNK_EXT):
                path = os.path.join(root, name)
                try:
                    os.remove(path)
                    removed.append(os.path.relpath(path, HERE))
                except OSError as exc:
                    print('  ! cannot remove %s: %s' % (os.path.relpath(path, HERE), exc))
    return sorted(removed)


# CLI entry point: select the scripts, run them, report what they wrote.
def main():
    ap = argparse.ArgumentParser(
        description='Run the scripts of this replication package (figures and tables)')
    ap.add_argument('--only', action='append', default=[], metavar='SUBSTR',
                    help='only run scripts whose path contains this substring (repeatable)')
    ap.add_argument('--paper-only', action='store_true',
                    help='only run the plotting scripts that back the paper figures')
    ap.add_argument('--plots-only', action='store_true',
                    help='only the plotting scripts (skip the tables)')
    ap.add_argument('--tables-only', action='store_true',
                    help='only the table/analysis scripts')
    ap.add_argument('--list', action='store_true',
                    help='list the scripts that would be run, then exit')
    ap.add_argument('--verbose', action='store_true',
                    help='also show the output of every script')
    ap.add_argument('--timeout', type=float, default=600.0,
                    help='per-script timeout in seconds')
    ap.add_argument('--clean', action='store_true',
                    help='only remove __pycache__/.vscode and other leftovers, then exit')
    ap.add_argument('--no-clean', action='store_true',
                    help='keep the leftovers instead of removing them after the run')
    args = ap.parse_args()

    if args.clean:
        print('cleaning temporary files under %s' % HERE)
        junk = clean()
        for path in junk:
            print('  %s' % path)
        print('%d item(s) removed.' % len(junk))
        return 0

    plots, tables = discover()
    if args.paper_only:
        wanted = {os.path.normpath(os.path.join(HERE, p)) for p in PAPER_FIGURES}
        plots = [s for s in plots if os.path.normpath(s) in wanted]
        tables = []
    if args.plots_only:
        tables = []
    if args.tables_only:
        plots = []
    for key in args.only:
        plots = [s for s in plots if key.lower() in s.lower()]
        tables = [s for s in tables if key.lower() in s.lower()]

    # Figures first: some analysis scripts read the CSV a figure script writes.
    scripts = plots + tables
    if not scripts:
        print('no script matched.')
        return 0
    if args.list:
        for label, group in (('figures', plots), ('tables', tables)):
            if not group:
                continue
            print('%s:' % label)
            for path in group:
                print('  %s' % os.path.relpath(path, HERE))
        print('\n%d scripts (%d plotting, %d table/analysis).'
              % (len(scripts), len(plots), len(tables)))
        return 0

    env = os.environ.copy()
    env['MPLBACKEND'] = 'Agg'
    env['PYTHONIOENCODING'] = 'utf-8'

    print('Replication Package: %s' % HERE)
    print('running %d scripts (%d plotting, %d table/analysis, Agg backend)...\n'
          % (len(scripts), len(plots), len(tables)))

    results, t_all = [], time.time()
    for i, path in enumerate(scripts, 1):
        rel = os.path.relpath(path, HERE)
        cwd = os.path.dirname(path)
        before = snapshot()
        t0 = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, path],
                cwd=cwd, env=env,
                capture_output=True, text=True, encoding='utf-8', errors='replace',
                timeout=args.timeout)
            code, out, err = proc.returncode, proc.stdout or '', proc.stderr or ''
            fail_msg = '' if code == 0 else (err.strip().splitlines() or
                                             out.strip().splitlines() or [''])[-1]
        except subprocess.TimeoutExpired:
            code, out, err = -1, '', ''
            fail_msg = 'timeout (> %gs)' % args.timeout
        dt = time.time() - t0

        after = snapshot()
        written = sorted(os.path.relpath(p, HERE) for p, m in after.items()
                         if before.get(p) != m)

        ok = (code == 0)
        results.append({'rel': rel, 'ok': ok, 'sec': dt, 'msg': fail_msg,
                        'written': written, 'out': out, 'err': err})
        mark = 'OK' if ok else 'FAIL'
        print('[%2d/%2d] %-4s %6.1fs  %s' % (i, len(scripts), mark, dt, rel))
        for w in written:
            print('           -> %s' % w)
        if not ok:
            print('           error: %s' % fail_msg)
            tail = [l for l in (err or out).strip().splitlines() if l.strip()][-6:]
            for line in tail:
                print('           | %s' % line)
        if args.verbose and ok and out.strip():
            for line in out.strip().splitlines():
                print('           | %s' % line)

    ok_n = sum(1 for r in results if r['ok'])
    print('\n================ summary ================')
    print('passed %d / %d, total %.1fs' % (ok_n, len(results), time.time() - t_all))
    if ok_n != len(results):
        print('failed:')
        for r in results:
            if not r['ok']:
                print('  - %s : %s' % (r['rel'], r['msg']))
    written = sorted({w for r in results if r['ok'] for w in r['written']})
    print('%d files written/updated:' % len(written))
    for w in written:
        print('  %s' % w)

    if args.no_clean:
        return 0 if ok_n == len(results) else 1
    junk = clean()
    print('\ncleaned %d temporary item(s):' % len(junk))
    for path in junk:
        print('  %s' % path)
    return 0 if ok_n == len(results) else 1


if __name__ == '__main__':
    sys.exit(main())
