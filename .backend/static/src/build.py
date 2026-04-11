#!/usr/bin/env python3
"""Build-time concatenator: merges split JS modules into monolithic index.html.

Preserves the single-file frontend constraint from agents.md while allowing
development in organized module files.

Usage:
    python build.py            Build index.html from base.html + js/*.js
    python build.py --watch    Auto-rebuild on file changes (dev mode)
    python build.py --verify   Build and compare against existing index.html
"""
import os
import sys
import glob
import time

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_HTML = os.path.join(SRC_DIR, "base.html")
JS_DIR = os.path.join(SRC_DIR, "js")
OUTPUT = os.path.join(SRC_DIR, "..", "index.html")

PLACEHOLDER = "/* __BUILD_JS__ */"


def build() -> str:
    """Concatenate base.html + sorted js/*.js → index.html. Returns output path."""
    with open(BASE_HTML, "r", encoding="utf-8") as f:
        template = f.read()

    if PLACEHOLDER not in template:
        print(f"ERROR: Placeholder '{PLACEHOLDER}' not found in base.html", file=sys.stderr)
        sys.exit(1)

    js_files = sorted(glob.glob(os.path.join(JS_DIR, "*.js")))
    if not js_files:
        print("WARNING: No .js files found in src/js/", file=sys.stderr)

    segments = []
    for f in js_files:
        with open(f, "r", encoding="utf-8") as fh:
            content = fh.read()
        segments.append(content)

    combined_js = "".join(segments)
    output_content = template.replace(PLACEHOLDER, combined_js)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(output_content)

    print(f"Built {os.path.relpath(OUTPUT, SRC_DIR)} ({len(output_content):,} bytes, {len(js_files)} modules)")
    return OUTPUT


def verify():
    """Build and compare against existing index.html (pre-split backup)."""
    backup = OUTPUT + ".bak"
    if not os.path.exists(backup):
        print(f"No backup found at {backup}. Run with --verify after creating a .bak")
        sys.exit(1)

    build()

    with open(OUTPUT, "r", encoding="utf-8") as f:
        new = f.read()
    with open(backup, "r", encoding="utf-8") as f:
        old = f.read()

    # Normalize line endings for comparison
    new_norm = new.replace('\r\n', '\n').strip()
    old_norm = old.replace('\r\n', '\n').strip()

    if new_norm == old_norm:
        print("✅ VERIFY PASSED: Built output matches backup exactly.")
    else:
        # Find first difference
        new_lines = new_norm.split('\n')
        old_lines = old_norm.split('\n')
        for i, (nl, ol) in enumerate(zip(new_lines, old_lines), 1):
            if nl != ol:
                print(f"❌ VERIFY FAILED: First diff at line {i}")
                print(f"  OLD: {ol[:100]}")
                print(f"  NEW: {nl[:100]}")
                break
        else:
            diff_len = abs(len(new_lines) - len(old_lines))
            print(f"❌ VERIFY FAILED: Line count differs by {diff_len} (old={len(old_lines)}, new={len(new_lines)})")
        sys.exit(1)


def watch():
    """Auto-rebuild on file changes."""
    print("Watching for changes... (Ctrl+C to stop)")
    mtimes = {}
    build()  # Initial build

    try:
        while True:
            changed = False
            watch_files = [BASE_HTML] + sorted(glob.glob(os.path.join(JS_DIR, "*.js")))
            for f in watch_files:
                try:
                    mt = os.path.getmtime(f)
                except OSError:
                    continue
                if mtimes.get(f) != mt:
                    mtimes[f] = mt
                    changed = True

            if changed:
                try:
                    build()
                except Exception as e:
                    print(f"Build error: {e}", file=sys.stderr)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped watching.")


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch()
    elif "--verify" in sys.argv:
        verify()
    else:
        build()
