"""Rebuilds the song table in README.md from the song files themselves.

Every song lives in its own folder under songs/, holding its .midicraft file and any extras
(a .litematic, a .schem, ...). The table is read from what each .midicraft file says about
itself (Song details in Midicraft): the name gives the song and artist, Credits the arranger
and site, and Description the video link. So adding a song is: make its folder, drop the files
in, run this. Only the part of README.md between the two markers is rewritten.

    python update-readme.py
"""
import gzip
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
SONGS = ROOT / "songs"
README = ROOT / "README.md"
RAW = "https://github.com/ekra8154/Midicraft-songs/raw/main/"
START = "<!-- songs:start -->"
END = "<!-- songs:end -->"
TAG = " (smelvincreations)"
# What the Download column links, in this order. The .midicraft stays in every folder, but until
# Midicraft is out the schematics are what people can use; add ".midicraft" back here then.
LISTED = (".litematic", ".schem")


def header_and_name(path):
    """The file's header and the song's name. Gzipped or not, as the mod reads it."""
    data = path.read_bytes()
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    root = json.loads(data.decode("utf8"))
    if "midicraft" in root and "song" in root:
        return root["midicraft"], root["song"].get("name", path.stem)
    return {}, root.get("name", path.stem)


def row(folder):
    songs = sorted(folder.glob("*.midicraft"))
    if not songs:
        return None
    song_file = songs[0]
    header, name = header_and_name(song_file)
    title = name[:-len(TAG)] if name.endswith(TAG) else name
    song, _, artist = title.partition(" - ")
    credits = header.get("credits") or ""
    source = header.get("source") or ""
    kind = ("MIDI" if source.startswith("MIDI") else "NBS" if source.startswith("NBS")
            else "NBS" if "noteblock world" in credits.lower() else "MIDI")
    arranged = f"{kind} by {credits}" if credits else ""
    video = re.search(r"https?://\S+", header.get("description") or "")
    video = f"[Watch]({video.group(0)})" if video else ""

    files = sorted(path for path in folder.iterdir() if path.is_file())

    def link(path):
        # Named by what follows the tag where a folder holds two of one kind, so the 23x1 build
        # and a build with its scenery read apart: "23x1 .litematic", "with tree .litematic".
        label = path.suffix
        if sum(other.suffix == path.suffix for other in files) > 1:
            tail = path.stem.split("smelvincreations-", 1)
            label = (tail[1].replace("-", " ") + " " if len(tail) == 2 else "") + path.suffix
        return f"[{label}]({RAW}{quote(path.relative_to(ROOT).as_posix())})"

    downloads = [link(path) for kind in LISTED for path in files if path.suffix == kind]
    return song.strip(), f"| {song.strip()} | {artist.strip()} | {arranged} | {video} | {', '.join(downloads)} |"


def main():
    rows = sorted(filter(None, (row(folder) for folder in SONGS.iterdir() if folder.is_dir())),
                  key=lambda entry: entry[0].lower())
    table = "\n".join(["| Song | Artist | Arranged from | Video | Download |",
                       "|---|---|---|---|---|"] + [line for _, line in rows])
    text = README.read_text(encoding="utf8")
    if START not in text or END not in text:
        sys.exit(f"README.md needs the {START} and {END} markers around the table")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    README.write_text(f"{before}{START}\n{table}\n{END}{after}", encoding="utf8", newline="\n")
    print(f"{len(rows)} songs in README.md")


if __name__ == "__main__":
    main()
