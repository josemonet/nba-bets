"""Build a skill for upload to Claude in two forms:
  dist/<name>.zip        one self-contained SKILL.md: references become appendices and each script a fenced block that Step 0a's
                         command copies back out to disk (the form the user's claude.ai skills use)
  dist/<name>-files.zip  the multi-file folder as it lives in skills/<name>/
Usage: python tools/build_single.py nfl-player-props
The script checks that the extraction command in the single file reproduces every script byte for byte and that the engine imports.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FENCE = "`" * 3

CONFIG = {
    "nfl-player-props": dict(
        refs=[("A", "references/sources.md", "Sources: where to get data, odds, injuries, weather and news"),
              ("B", "references/calibration.md", "Calibration: what the v1.0 engine is fitted on, and how it tested"),
              ("C", "references/markets.md", "Markets: how NFL props settle, and the rules that change a payout")],
        scripts=[("D", "scripts/nfl_props.py", "The engine (nfl_props.py v1.0)"),
                 ("E", "scripts/nfl_inputs.py", "The input builder (nfl_inputs.py)")],
        check="import nfl_props as m, nfl_inputs as d; print('engine version', m.VERSION)",
        files_section=(
            "## Files in this skill\n"
            "Everything lives in this one file:\n"
            "- SKILL.md (this file): the workflow, then five appendices.\n"
            "- Appendix A (was references/sources.md): where to get data, odds, injuries, weather and news, the 30-day pulse rules, and the Dead ends list. Read it before fetching anything.\n"
            "- Appendix B (was references/calibration.md): every fitted constant, the data behind it, the old value it replaced, and the walk-forward backtest against the old football_model. Read it when a number in this file needs its source, or before changing the engine.\n"
            "- Appendix C (was references/markets.md): how every NFL prop settles (gross passing yards, kneel-downs, overtime, anytime-TD rules, voids, pushes, stat corrections) and the house rules that change a payout. Read it before pricing an unfamiliar market.\n"
            "- Appendix D (was scripts/nfl_props.py): the engine (Step 9). Appendix E (was scripts/nfl_inputs.py): the input builder that downloads nflverse data and builds every engine input the way the backtest did (Step 3). The command in Step 0a copies both out of this file into the working directory; never retype them from memory.\n"),
    ),
}


def load_block(name, cfg):
    names = [os.path.basename(p) for _, p, _ in cfg["scripts"]]
    lst = ", ".join(repr(n) for n in names)
    return (
        f"- Load the engine (once per session, about 1 min): run this command. It copies Appendices "
        f"{' and '.join(k for k, _, _ in cfg['scripts'])} out of this file into {' and '.join(names)} in the working directory, "
        f"so nothing is retyped, then checks the version.\n"
        f"{FENCE}bash\n"
        "python3 - <<'EOF'\n"
        "import subprocess\n"
        "fence = '`'*3\n"
        f"found = subprocess.run(\"find / -name SKILL.md -path '*{name}*' 2>/dev/null\", shell=True,\n"
        "                       capture_output=True, text=True).stdout.splitlines()\n"
        "for path in sorted(found, key=lambda p: '/skills/' not in p):\n"
        "    lines = open(path, encoding='utf-8').read().split('\\n')\n"
        f"    if all(fence+'python '+n in lines for n in ({lst},)):\n"
        f"        for n in ({lst},):\n"
        "            a = lines.index(fence+'python '+n)+1; b = lines.index(fence, a)\n"
        "            open(n, 'w', encoding='utf-8').write('\\n'.join(lines[a:b])+'\\n')\n"
        "            print(n, 'copied from', path, '(', b-a, 'lines)')\n"
        "        break\n"
        "else:\n"
        f"    print('no copy of this skill on disk: write each appendix to its file exactly as printed')\n"
        "EOF\n"
        f"python3 -c \"{cfg['check']}\"\n"
        f"{FENCE}\n"
    )


def single_file(name):
    cfg = CONFIG[name]; base = os.path.join(ROOT, "skills", name)
    s = open(os.path.join(base, "SKILL.md"), encoding="utf-8").read()
    a, b = s.index("## Files in this skill"), s.index("## Skills built into this one")
    s = s[:a] + "<!-- files -->\n" + s[b:]
    a, b = s.index("<!-- load -->\n"), s.index("<!-- /load -->\n") + len("<!-- /load -->\n")
    s = s[:a] + load_block(name, cfg) + s[b:]
    s = s.replace("(scripts/nfl_props.py v1.0, scripts/nfl_inputs.py)", "(nfl_props.py v1.0 and nfl_inputs.py, Appendices D and E)")
    s = s.replace("Copy both files into the working directory and import them.", "Step 0a copies both out of this file; import them.")
    s = s.replace("and scripts/nfl_props.py, with no thesis", "and the engine (Appendix D), with no thesis")
    for k, path, _ in cfg["refs"]:
        s = s.replace(path, f"Appendix {k}")
    for k, path, _ in cfg["scripts"]:
        s = s.replace(path, f"{os.path.basename(path)} (Appendix {k})")
    s = s.replace("<!-- files -->\n", cfg["files_section"] + "\n")                  # after the path rewrite, so "was ..." survives
    for k, path, title in cfg["refs"]:
        t = open(os.path.join(base, path), encoding="utf-8").read().split("\n")
        t = t[1:] if t and t[0].startswith("# ") else t                       # the file's own title becomes the appendix title
        t = [("#" + ln) if re.match(r"^#{2,5} ", ln) else ln for ln in t]
        s = s.rstrip("\n") + f"\n\n## Appendix {k}. {title}\n" + "\n".join(t).rstrip("\n") + "\n"
    for k, path, title in cfg["scripts"]:
        code = open(os.path.join(base, path), encoding="utf-8").read().rstrip("\n")
        s += f"\n## Appendix {k}. {title}\n{FENCE}python {os.path.basename(path)}\n{code}\n{FENCE}\n"
    prose = s[:s.index(f"## Appendix {cfg['scripts'][0][0]}.")].replace(cfg["files_section"], "")   # embedded code stays byte for byte
    assert "references/" not in prose and "scripts/" not in prose, "a file path survived the merge"
    assert not re.search(r"\$\d", s), "dollar sign before digits"
    return s


def verify(name, skill_text):
    cfg = CONFIG[name]; base = os.path.join(ROOT, "skills", name)
    cmd = re.search(FENCE + r"bash\n(python3 - <<'EOF'.*?)" + FENCE, skill_text, re.S).group(1)
    with tempfile.TemporaryDirectory() as tmp:
        sk = os.path.join(tmp, "skills", name); os.makedirs(sk)
        open(os.path.join(sk, "SKILL.md"), "w", encoding="utf-8").write(skill_text)
        cmd = cmd.replace("find / -name SKILL.md", f"find {tmp} -name SKILL.md")
        out = subprocess.run(["bash", "-c", cmd], cwd=tmp, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        for _, path, _ in cfg["scripts"]:
            got = open(os.path.join(tmp, os.path.basename(path)), encoding="utf-8").read()
            assert got == open(os.path.join(base, path), encoding="utf-8").read(), f"{path} differs after extraction"
        print(out.stdout.strip())


def main(name):
    s = single_file(name)
    verify(name, s)
    dist = os.path.join(ROOT, "dist"); os.makedirs(dist, exist_ok=True)
    one = os.path.join(dist, name); shutil.rmtree(one, ignore_errors=True); os.makedirs(one)
    open(os.path.join(one, "SKILL.md"), "w", encoding="utf-8").write(s)
    with zipfile.ZipFile(os.path.join(dist, f"{name}.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(one, "SKILL.md"), f"{name}/SKILL.md")
    with zipfile.ZipFile(os.path.join(dist, f"{name}-files.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        base = os.path.join(ROOT, "skills", name)
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for f in sorted(fn):
                if not f.endswith(".pyc"):
                    full = os.path.join(dp, f); z.write(full, os.path.join(name, os.path.relpath(full, base)))
    print(f"dist/{name}.zip: single SKILL.md, {len(s)/1024:.0f} KB, {s.count(chr(10))} lines")
    print(f"dist/{name}-files.zip: " + ", ".join(zipfile.ZipFile(os.path.join(dist, f"{name}-files.zip")).namelist()))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "nfl-player-props")
