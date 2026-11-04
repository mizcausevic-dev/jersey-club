#!/usr/bin/env python3
"""Independent read-back validator for final Footwork Codex artifact bytes."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import build_footwork as spec


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def norm(events: list[dict]) -> list[tuple[int, int, int, int, int]]:
    return sorted((row["start"], row["duration"], row["pitch"], row["velocity"], row["channel"]) for row in events)


def overlaps(events: list[dict], mono: bool = False) -> bool:
    if mono:
        latest = -1
        for row in sorted(events, key=lambda item: (item["start"], item["pitch"])):
            if row["start"] < latest:
                return True
            latest = row["start"] + row["duration"]
        return False
    last: dict[int, int] = {}
    for row in sorted(events, key=lambda item: (item["start"], item["pitch"])):
        if row["start"] < last.get(row["pitch"], -1):
            return True
        last[row["pitch"]] = row["start"] + row["duration"]
    return False


def first_video_stream(probe: dict) -> dict | None:
    return next((item for item in probe.get("streams", []) if item.get("codec_type") == "video"), None)


def media_duration(probe: dict) -> float:
    return float(probe.get("format", {}).get("duration", 0))


def negative_control(root: Path) -> bool:
    fixture = root / "checks" / "fixtures" / "invalid-same-pitch-overlap.mid"
    data = spec.common_meta("negative fixture")
    data.extend([
        (0, 3, bytes([144, 60, 80])),
        (240, 3, bytes([144, 60, 80])),
        (720, 2, bytes([128, 60, 0])),
        (720, 2, bytes([128, 60, 0])),
    ])
    fixture.write_bytes(spec.midi(0, [spec.track(data)]))
    parsed = spec.parse_midi(fixture)
    return overlaps(parsed["tracks"][0]["events"])


def add_error(errors: list[str], text: str) -> None:
    if text not in errors:
        errors.append(text)


def validate(root: Path) -> dict:
    errors, warnings, midi_records = [], [], []
    midi_root = root / "midi"
    midi_files = sorted(midi_root.rglob("*.mid"))
    if len(midi_files) != 28:
        add_error(errors, "expected 28 MIDI files, found " + str(len(midi_files)))
    expected_names = {role for role, *_ in spec.ROLES}
    combined_files = [path for path in midi_files if path.name.endswith("-combined.mid")]
    role_files = [path for path in midi_files if path.name[:-4] in expected_names]
    if len(combined_files) != 4 or len(role_files) != 24:
        add_error(errors, "MIDI export count does not match four combined and 24 role files")
    parsed_files: dict[Path, dict] = {}
    for path in midi_files:
        record = {"path": path.relative_to(root).as_posix(), "sha256": hash_file(path), "bytes": path.stat().st_size, "errors": []}
        try:
            parsed = spec.parse_midi(path)
            parsed_files[path] = parsed
            expected_format = 1 if path.name.endswith("-combined.mid") else 0
            if parsed["format"] != expected_format:
                record["errors"].append("format")
            if parsed["division"] != spec.PPQ:
                record["errors"].append("ppq")
            all_events = [event for track in parsed["tracks"] for event in track["events"]]
            if not all_events:
                record["errors"].append("zero_notes")
            metas = [meta for track in parsed["tracks"] for meta in track["metas"]]
            if not any(kind == 81 and int.from_bytes(body, "big") == spec.TEMPO_US for _, kind, body in metas):
                record["errors"].append("tempo")
            if not any(kind == 88 and body == bytes([4, 2, 24, 8]) for _, kind, body in metas):
                record["errors"].append("meter")
            for track in parsed["tracks"]:
                if track["eot"] != spec.END_TICK:
                    record["errors"].append("end_tick")
                if track["forbidden"]:
                    record["errors"].append("forbidden_messages")
                for event in track["events"]:
                    if event["duration"] <= 0 or event["start"] < 0 or event["start"] + event["duration"] > spec.END_TICK:
                        record["errors"].append("event_timing")
                    if not 0 <= event["pitch"] <= 127 or not 1 <= event["velocity"] <= 127:
                        record["errors"].append("note_range")
                if overlaps(track["events"]):
                    record["errors"].append("same_pitch_overlap")
            if expected_format == 0:
                role = path.stem
                track = parsed["tracks"][0]
                actual_channels = {event["channel"] for event in track["events"]}
                if actual_channels != {spec.ROLE[role][2]}:
                    record["errors"].append("channel")
                if role in ("sub_bass", "principal_motif") and overlaps(track["events"], mono=True):
                    record["errors"].append("monophonic_role")
            else:
                names = [track["name"] for track in parsed["tracks"]]
                if not all(role in names for role, *_ in spec.ROLES):
                    record["errors"].append("combined_track_names")
        except Exception as exc:
            record["errors"].append("parse: " + str(exc))
        if record["errors"]:
            add_error(errors, record["path"] + ": " + ", ".join(sorted(set(record["errors"]))))
        midi_records.append(record)

    for study in spec.STUDIES:
        folder = midi_root / (study["id"] + "-" + study["slug"])
        combined_path = folder / (study["id"] + "-" + study["slug"] + "-combined.mid")
        if combined_path not in parsed_files:
            continue
        combined = parsed_files[combined_path]
        by_name = {track["name"]: track["events"] for track in combined["tracks"]}
        for role, *_ in spec.ROLES:
            role_path = folder / (role + ".mid")
            if role_path not in parsed_files or role not in by_name:
                add_error(errors, study["id"] + " is missing comparison source for " + role)
                continue
            if norm(parsed_files[role_path]["tracks"][0]["events"]) != norm(by_name[role]):
                add_error(errors, study["id"] + " combined events disagree with " + role)

    notes_csv = root / "catalog" / "note-events-Codex.csv"
    csv_events: dict[tuple[str, str], list[tuple[int, int, int, int, int]]] = {}
    try:
        with notes_csv.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                key = (row["study_id"], row["role"])
                csv_events.setdefault(key, []).append((int(row["start_tick"]), int(row["duration_tick"]), int(row["pitch"]), int(row["velocity"]), int(row["user_facing_channel"]) - 1))
        for study in spec.STUDIES:
            folder = midi_root / (study["id"] + "-" + study["slug"])
            for role, *_ in spec.ROLES:
                role_path = folder / (role + ".mid")
                if role_path in parsed_files:
                    expected = norm(parsed_files[role_path]["tracks"][0]["events"])
                    actual = sorted(csv_events.get((study["id"], role), []))
                    if actual != expected:
                        add_error(errors, "CSV event mismatch for " + study["id"] + " " + role)
    except Exception as exc:
        add_error(errors, "canonical note CSV error: " + str(exc))

    regions_csv = root / "catalog" / "structural-regions-Codex.csv"
    try:
        groups: dict[str, list[dict]] = {}
        with regions_csv.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                groups.setdefault(row["study_id"], []).append(row)
        for study in spec.STUDIES:
            prior = 0
            rows = sorted(groups.get(study["id"], []), key=lambda row: int(row["start_tick"]))
            if len(rows) != 4:
                add_error(errors, "region count for " + study["id"])
                continue
            for row in rows:
                start, end = int(row["start_tick"]), int(row["end_tick"])
                if start != prior or end <= start:
                    add_error(errors, "region coverage gap or overlap for " + study["id"])
                prior = end
            if prior != spec.END_TICK:
                add_error(errors, "region coverage end for " + study["id"])
    except Exception as exc:
        add_error(errors, "region CSV error: " + str(exc))

    try:
        mapped = {row["pitch"] for row in spec.DRUM_MAP}
        used = set()
        for study in spec.STUDIES:
            drum_path = midi_root / (study["id"] + "-" + study["slug"]) / "drums.mid"
            if drum_path in parsed_files:
                used.update(event["pitch"] for event in parsed_files[drum_path]["tracks"][0]["events"])
        if not used.issubset(mapped) or not mapped.issubset(used):
            add_error(errors, "drum map does not cover actual drum events")
    except Exception as exc:
        add_error(errors, "drum map error: " + str(exc))

    archive = root / "downloads" / "footwork-codex-midi.zip"
    try:
        with zipfile.ZipFile(archive) as package:
            names = package.namelist()
            if any(name.startswith("/") or ".." in Path(name).parts or "\\" in name for name in names):
                add_error(errors, "ZIP has unsafe member path")
            expected = {path.relative_to(root).as_posix() for path in midi_files}
            if not expected.issubset(set(names)):
                add_error(errors, "ZIP is missing MIDI members")
            for name in names:
                if name.endswith(".mid"):
                    temporary = root / "checks" / "fixtures" / ("zip-" + Path(name).name)
                    temporary.write_bytes(package.read(name))
                    spec.parse_midi(temporary)
                    temporary.unlink()
    except Exception as exc:
        add_error(errors, "ZIP validation error: " + str(exc))

    media = {
        "preview": root / "preview" / "footwork-preview.mp3",
        "film": root / "film" / "footwork-preview.mp4",
        "hero": root / "art" / "hero.jpg",
        "square": root / "art" / "square.jpg",
        "instagram_square": root / "social" / "instagram-Codex" / "footwork-square.jpg",
        "instagram_portrait": root / "social" / "instagram-Codex" / "footwork-portrait.jpg",
        "x_image": root / "social" / "x-Codex" / "footwork-card.jpg",
    }
    probes = {}
    for name, path in media.items():
        try:
            probes[name] = spec.probe(path)
        except Exception as exc:
            add_error(errors, "media probe " + name + ": " + str(exc))
    if "preview" in probes and not any(row.get("codec_type") == "audio" for row in probes["preview"].get("streams", [])):
        add_error(errors, "preview has no audio stream")
    if "film" in probes:
        streams = {row.get("codec_type") for row in probes["film"].get("streams", [])}
        if not {"audio", "video"}.issubset(streams) or not 10 <= media_duration(probes["film"]) <= 40:
            add_error(errors, "film stream or duration contract")
    for name, width, height in [("hero",1280,720),("square",1080,1080),("instagram_square",1080,1080),("instagram_portrait",1080,1350),("x_image",1080,1080)]:
        stream = first_video_stream(probes.get(name, {}))
        if not stream or stream.get("width") != width or stream.get("height") != height:
            add_error(errors, name + " dimensions")

    vtt = root / "film" / "footwork-preview.vtt"
    try:
        captions = vtt.read_text(encoding="utf-8")
        if "preview, not a master" not in captions or "00:00:20.000" not in captions:
            add_error(errors, "VTT disclosure or timing")
    except Exception as exc:
        add_error(errors, "VTT error: " + str(exc))
    try:
        article = (root / "articles" / "medium-draft-Codex.md").read_text(encoding="utf-8")
        tags = next(line for line in article.splitlines() if line.startswith("Tags:"))
        if not article.startswith("# DRAFT") or "Call to action:" not in article or len([item for item in tags.split(":", 1)[1].split(",") if item.strip()]) > 5:
            add_error(errors, "article contract")
        x_lines = (root / "social" / "x-Codex" / "post-Codex.txt").read_text(encoding="utf-8").splitlines()
        if not x_lines or not x_lines[0].startswith("DRAFT") or len(x_lines[0]) > 280:
            add_error(errors, "X draft contract")
    except Exception as exc:
        add_error(errors, "draft validation error: " + str(exc))

    try:
        preview_manifest = json.loads((root / "preview" / "preview-manifest-Codex.json").read_text(encoding="utf-8"))
        source = root / preview_manifest["source_midi_path"]
        if hash_file(source) != preview_manifest["source_midi_sha256"] or hash_file(root / preview_manifest["preview_path"]) != preview_manifest["preview_sha256"]:
            add_error(errors, "preview provenance hash")
        film_manifest = json.loads((root / "film" / "video-manifest-Codex.json").read_text(encoding="utf-8"))
        if hash_file(root / film_manifest["source_audio_path"]) != film_manifest["source_audio_sha256"]:
            add_error(errors, "video source audio hash")
    except Exception as exc:
        add_error(errors, "provenance validation error: " + str(exc))

    checksum_path = root / "catalog" / "checksums-Codex.json"
    if checksum_path.exists():
        try:
            manifest = json.loads(checksum_path.read_text(encoding="utf-8"))
            for row in manifest["files"]:
                path = root / row["path"]
                if not path.exists() or path.stat().st_size != row["bytes"] or hash_file(path) != row["sha256"]:
                    add_error(errors, "checksum mismatch " + row["path"])
        except Exception as exc:
            add_error(errors, "checksum manifest error: " + str(exc))
    else:
        warnings.append("checksum manifest not present on initial validation pass")

    if not negative_control(root):
        add_error(errors, "negative same-pitch-overlap control did not fail as expected")
    return {
        "status": "PASS" if not errors else "FAIL",
        "run_time_utc": datetime.now(timezone.utc).isoformat(),
        "tool": "validate_footwork.py with Python " + sys.version.split()[0],
        "files_checked": len(midi_files),
        "errors": errors,
        "warnings": warnings,
        "midi_files": midi_records,
        "media": {name: {"path": path.relative_to(root).as_posix(), "sha256": hash_file(path)} for name, path in media.items() if path.exists()},
        "negative_control": {"path": "checks/fixtures/invalid-same-pitch-overlap.mid", "expected_result": "rejected for same-pitch overlap", "passed": not errors or "negative same-pitch-overlap control did not fail as expected" not in errors},
        "limitations": ["Automated validation only.", "Nobody auditioned these files.", "Duplicate detection is structural within this pack, not exhaustive copyright clearance."],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1], type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    report = validate(root)
    target = root / "checks" / "validation-report-Codex.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "errors": len(report["errors"]), "warnings": len(report["warnings"]), "report": target.relative_to(root).as_posix()}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
