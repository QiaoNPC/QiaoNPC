from pathlib import Path
import os
import re
import shutil
import subprocess
import textwrap


FRAME_DIR = Path("frames_cve")
OUT_GIF = Path("cve-showcase.gif")

# gifos reads these on import and will otherwise wipe ./frames and output.gif.
os.environ["GIFOS_FILES_FRAME_FOLDER_NAME"] = str(FRAME_DIR)
os.environ["GIFOS_FILES_OUTPUT_GIF_NAME"] = OUT_GIF.stem

import gifos


def detect_pattern(frames_dir: Path, prefix: str = "frame_", ext: str = ".png") -> str:
    frames = sorted(frames_dir.glob(f"{prefix}*{ext}"))
    if not frames:
        raise FileNotFoundError(f"No frames found in {frames_dir}")
    match = re.match(rf"^{re.escape(prefix)}(\d+){re.escape(ext)}$", frames[0].name)
    if not match:
        return f"{prefix}%03d{ext}"
    width = len(match.group(1))
    return f"{prefix}%0{width}d{ext}" if width > 1 else f"{prefix}%d{ext}"


def ffmpeg_gif(frames_dir: Path, fps: int, out_gif: Path, end_pause_sec: int = 5) -> None:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH")

    pattern = detect_pattern(frames_dir)
    inp = frames_dir / pattern
    palette = frames_dir / "palette.png"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(inp),
            "-vf",
            "palettegen",
            "-update",
            "1",
            "-frames:v",
            "1",
            str(palette),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ,
    )

    lavfi = "paletteuse"
    if end_pause_sec > 0:
        lavfi = f"tpad=stop_mode=clone:stop_duration={end_pause_sec},{lavfi}"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(inp),
            "-i",
            str(palette),
            "-lavfi",
            lavfi,
            str(out_gif),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=os.environ,
    )


def pad(value: str, width: int) -> str:
    return value[:width].ljust(width)


def wrap_entry(cve: str, title: str, title_width: int) -> list[str]:
    lines = textwrap.wrap(
        title,
        width=title_width,
        break_long_words=False,
        break_on_hyphens=False,
    )
    if not lines:
        lines = [""]
    rows = [f"{pad(cve, 15)} | {pad(lines[0], title_width)}"]
    rows.extend(f"{' ' * 15} | {pad(line, title_width)}" for line in lines[1:])
    return rows


if __name__ == "__main__":
    cves = [
        (
            "CVE-2026-33638",
            "Authenticated user-list exposed data via public /api/allusers endpoint",
        ),
        (
            "CVE-2026-33645",
            "Path Traversal Arbitrary File Write in /api/uploadChunked",
        ),
        (
            "CVE-2026-34376",
            "Password-protected share bypass via direct serve endpoint",
        ),
        (
            "CVE-2026-34072",
            "Middleware authentication bypass enabling unauthorized page access and server-action execution",
        ),
        (
            "CVE-2026-34832",
            "Cross-Account Feedback Deletion (IDOR)",
        ),
        (
            "CVE-2026-35052",
            "Remote Code Execution through redis/shelf storage",
        ),
        (
            "CVE-2026-39355",
            "Missing Authorization in TeamController::transferOwnership() Allows Any Authenticated User to Hijack Any Team (Broken Access Control)",
        ),
        (
            "CVE-2026-39901",
            "Protected Transactions Deletable via PUT",
        ),
        (
            "CVE-2026-40184",
            "Unauthenticated Access to Uploaded Files in TREK",
        ),
    ]

    G = "\x1b[32m"
    C = "\x1b[36m"
    Y = "\x1b[33m"
    W = "\x1b[37m"
    DIM = "\x1b[90m"
    B = "\x1b[1m"
    Z = "\x1b[0m"

    terminal = gifos.Terminal(width=920, height=420, xpad=8, ypad=8)
    fps = 15
    title_width = 58
    prompt = f"{G}qiao@dllm{Z}:{C}~/cves{Z}$ "

    def type_line(row: int, value: str, prefix: str = "", pre: str = "", post: str = "") -> None:
        buffer = pre + prefix
        for ch in value:
            buffer += ch
            terminal.delete_row(row_num=row)
            terminal.gen_text(text=buffer + post + Z, row_num=row, contin=True)

    def line(row: int, value: str, count: int = 3) -> None:
        terminal.delete_row(row_num=row)
        terminal.gen_text(text=value + Z, row_num=row, contin=True, count=count)

    row = 1
    line(row, f"{B}{W}Initializing advisory console...", count=6)
    row += 1

    type_line(row, "cvectl sync --owner QiaoNPC --year 2026", prefix=prompt)
    row += 1
    line(row, f"{G}OK{Z}    loaded {len(cves)} published CVEs into local index", count=5)
    row += 1

    type_line(row, "cvectl list --format table --fields cve,title", prefix=prompt)
    row += 1
    line(row, f"{W}Portfolio:{Z} {len(cves)} CVEs   {W}Focus:{Z} web / appsec / platform", count=5)
    row += 1
    line(row, f"{W}{pad('CVE', 15)} | {pad('FINDING', title_width)}", count=4)
    row += 1
    line(row, f"{DIM}{'-' * 15}-+-{'-' * title_width}", count=3)
    row += 1

    for cve, title in cves:
        for entry_row in wrap_entry(cve, title, title_width):
            line(row, f"{W}{entry_row}", count=3)
            row += 1

    line(row, f"{Y}READY{Z}  advisory showcase compiled for README", count=12)

    ffmpeg_gif(frames_dir=FRAME_DIR, fps=fps, out_gif=OUT_GIF, end_pause_sec=5)
    shutil.rmtree(FRAME_DIR, ignore_errors=True)
