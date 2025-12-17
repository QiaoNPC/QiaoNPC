from dotenv import load_dotenv
from pathlib import Path
import os
import re
import shutil
import subprocess
import json
import urllib.request
import urllib.error

load_dotenv(Path(__file__).with_name(".env"), override=True)
import gifos


def detect_pattern(frames_dir: Path, prefix="frame_", ext=".png") -> str:
    frames = sorted(frames_dir.glob(f"{prefix}*{ext}"))
    if not frames:
        raise FileNotFoundError(f"No frames found in {frames_dir}")
    m = re.match(rf"^{re.escape(prefix)}(\d+){re.escape(ext)}$", frames[0].name)
    if not m:
        return f"{prefix}%03d{ext}"
    w = len(m.group(1))
    return f"{prefix}%0{w}d{ext}" if w > 1 else f"{prefix}%d{ext}"


def ffmpeg_gif(frames_dir="frames", fps=8, out_gif="output.gif", end_pause_sec=3):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH")

    frames_dir = Path(frames_dir)
    pattern = detect_pattern(frames_dir)
    inp = frames_dir / pattern
    palette = frames_dir / "palette.png"
    out_gif = Path(out_gif)

    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(inp),
         "-vf", "palettegen", "-update", "1", "-frames:v", "1", str(palette)],
        check=True,
        env=os.environ,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    lavfi = "paletteuse"
    if end_pause_sec and end_pause_sec > 0:
        lavfi = f"tpad=stop_mode=clone:stop_duration={end_pause_sec},{lavfi}"

    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(fps), "-i", str(inp), "-i", str(palette),
         "-lavfi", lavfi, str(out_gif)],
        check=True,
        env=os.environ,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    print(str(out_gif.resolve()))


def fetch_pinned_repos(login: str, token: str, first: int = 6):
    q = """
    query($login:String!, $first:Int!) {
      user(login: $login) {
        pinnedItems(first: $first, types: REPOSITORY) {
          nodes {
            ... on Repository { name }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": q, "variables": {"login": login, "first": first}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "make_gif.py",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.loads(r.read().decode("utf-8"))
    nodes = (((data.get("data") or {}).get("user") or {}).get("pinnedItems") or {}).get("nodes") or []
    return [n.get("name") for n in nodes if isinstance(n, dict) and n.get("name")]


def clean_workshop_name(n: str) -> str:
    return n.replace("-Workshop-Materials", "").replace("_Workshop", "").replace("_", "-")


def pad(s: str, w: int) -> str:
    s = s if s is not None else ""
    return s[:w].ljust(w)


if __name__ == "__main__":
    out_gif = Path("output.gif")
    frames = Path("frames")
    if out_gif.exists():
        out_gif.unlink()
    if frames.exists():
        shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir(parents=True, exist_ok=True)

    G = "\x1b[32m"
    C = "\x1b[36m"
    Y = "\x1b[33m"
    W = "\x1b[37m"
    DIM = "\x1b[90m"
    B = "\x1b[1m"
    Z = "\x1b[0m"

    t = gifos.Terminal(width=920, height=480, xpad=8, ypad=8)

    def type_line(row, s, prefix="", pre="", post=""):
        buf = pre + prefix
        for ch in s:
            buf += ch
            t.delete_row(row_num=row)
            t.gen_text(text=buf + post + Z, row_num=row, contin=True)

    def line(row, s):
        t.delete_row(row_num=row)
        t.gen_text(text=s + Z, row_num=row, contin=True)

    user = "QiaoNPC"
    followers = "?"
    stars = "?"
    commits = "?"
    rank = "?"

    try:
        s = gifos.utils.fetch_github_stats(user_name=user)
        followers = str(getattr(s, "total_followers", "?"))
        stars = str(getattr(s, "total_stargazers", "?"))
        commits = str(getattr(s, "total_commits_all_time", "?"))
        rnk = getattr(s, "user_rank", None)
        rank = getattr(rnk, "level", "?") if rnk else "?"
    except Exception:
        pass

    token = os.getenv("GITHUB_TOKEN") or ""
    pinned = []
    try:
        if token:
            pinned = fetch_pinned_repos(user, token, first=6)
    except Exception:
        pinned = []

    workshops = [clean_workshop_name(n) for n in pinned if "workshop" in n.lower()]
    wcount = str(len(workshops)) if workshops else "?"

    certs = [
        ("HackTheBox CPTS", "Aug 2025"),
        ("TryHackMe Jr Penetration Tester (PT1)", "Aug 2025"),
        ("CyberWarfare Red Team Analyst (CRTA)", "Jun 2025"),
        ("Comptia Pentest+", "Mar 2025"),
        ("Certified Mobile Pentester (CMPen - Android)", "Feb 2025"),
        ("Certified Mobile Pentester (CMPen - iOS)", "Jan 2025"),
        ("Certified AppSec Practitioner (CAP)", "Nov 2024"),
        ("Certified Network Security Practitioner (CNSP)", "Jun 2024"),
    ]

    host = "qiao@dllm"
    pwd = "~/"
    prompt = f"{G}{host}{Z}:{C}{pwd}{Z}$ "

    r = 1
    line(r, f"{B}{W}Initializing secure console...")
    r += 1

    type_line(r, "githubctl stats --user QiaoNPC", prefix=prompt)
    r += 1
    line(r, f"{W}Followers:{Z} {followers}   {W}Stars:{Z} {stars}   {W}Commits:{Z} {commits}   {W}Rank:{Z} {rank}")
    r += 1

    type_line(r, "githubctl workshops --pinned --table", prefix=prompt)
    r += 1

    w_col1 = 2
    w_max = 60
    w_col2 = w_max - w_col1 - 3
    line(r, f"{W}Workshops:{Z} {wcount}")
    r += 1
    line(r, f"{W}{pad('#', w_col1)} | {pad('WORKSHOP', w_col2)}")
    r += 1
    line(r, f"{DIM}{'-'*w_col1}-+-{'-'*w_col2}")
    r += 1

    if workshops:
        for i, n in enumerate(workshops[:6], start=1):
            line(r, f"{W}{pad(str(i), w_col1)} | {pad(n, w_col2)}")
            r += 1
    else:
        line(r, f"{DIM}{pad('-', w_col1)} | {pad('n/a', w_col2)}")
        r += 1

    r += 1

    type_line(r, "certctl list --verified --table", prefix=prompt)
    r += 1

    c_col1 = 2
    c_col3 = 9
    c_max = 78
    c_col2 = c_max - c_col1 - c_col3 - 6
    line(r, f"{W}Certifications:{Z} {len(certs)}")
    r += 1
    line(r, f"{W}{pad('#', c_col1)} | {pad('CERTIFICATION', c_col2)} | {pad('DATE', c_col3)}")
    r += 1
    line(r, f"{DIM}{'-'*c_col1}-+-{'-'*c_col2}-+-{'-'*c_col3}")
    r += 1

    for i, (name, date) in enumerate(certs, start=1):
        line(r, f"{W}{pad(str(i), c_col1)} | {pad(name, c_col2)} | {pad(date, c_col3)}")
        r += 1

    r += 1

    type_line(r, "integrity --quick-check", prefix=prompt)
    r += 1
    line(r, f"{Y}WARN{Z}  2 configs drifted (restored from baseline)")
    r += 1
    line(r, f"{G}OK{Z}    package signatures verified")
    r += 1

    type_line(r, "printf 'READY\\n'", prefix=prompt)
    r += 1
    line(r, f"{G}{B}READY")
    r += 1

    ffmpeg_gif(frames_dir="frames", fps=10, out_gif="output.gif", end_pause_sec=5)
