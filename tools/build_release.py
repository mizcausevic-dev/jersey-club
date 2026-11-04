#!/usr/bin/env python3
"""Build one original, documented four-study MIDI release from an embedded pack profile."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import build_footwork as engine

PPQ = 480
BAR_TICKS = 1920
BARS = 32
END_TICK = 61440
SECTIONS = [("introduction", "Introduction", 0, 8), ("statement", "Statement", 8, 8), ("contrast", "Contrast", 16, 8), ("transformed_return", "Transformed return", 24, 8)]
ROLE_NAMES = ["chord_pulse", "sub_bass", "principal_motif", "vocal_like_synth", "counter_texture", "drums"]
DRUM_MAP = [
    {"pitch": 36, "name": "Kick", "purpose": "low rhythmic anchor"},
    {"pitch": 38, "name": "Snare", "purpose": "short answer"},
    {"pitch": 39, "name": "Clap", "purpose": "accent answer"},
    {"pitch": 42, "name": "Closed hi-hat", "purpose": "grid detail"},
    {"pitch": 46, "name": "Open hi-hat", "purpose": "transition marker"},
]

# These directions are production prompts for original symbolic studies, not cultural or historical descriptions.
PACKS = {
    "jersey-club": {"title": "Jersey Club Studies", "brief_name": "Jersey Club", "code": "jc", "bpm": 138, "root": 50, "mode": [0, 2, 3, 5, 7, 9, 10], "chord_steps": [0, 5, 3, 7], "intent": "Compact kinetic phrases with clearly differentiated rhythm cells.", "rhythm": "A repeating kick cell uses short stop-start answers; fast percussion appears only at transitions.", "palette": "Short synth stabs, monophonic bass, one reduced-instrumentation hook and selective complementary parts.", "guardrail": "No sampled signature chants or copied recognizable breaks; hooks and source sounds are original.", "studies": ["Latch Point", "Quickstep Relay", "Cut Window", "Voltage Return"], "colors": ["#f6eee0", "#251e21", "#ef5b3f", "#1769aa"], "pattern": 0},
    "baltimore-club": {"title": "Baltimore Club Studies", "brief_name": "Baltimore Club", "code": "bc", "bpm": 130, "root": 48, "mode": [0, 2, 3, 5, 7, 8, 10], "chord_steps": [0, 3, 5, 2], "intent": "Direct percussive movement and playful structural interruption.", "rhythm": "Original broken drum cells keep a firm anchor, alternate one-bar responses, then expose a silent turnaround.", "palette": "Punchy original percussion, synthetic bass, clipped keys and melodic punctuation.", "guardrail": "This direction does not claim cultural authenticity or conflate regional club styles.", "studies": ["Sidechain Alley", "Flash Count", "Corner Answer", "Sixteen Back"], "colors": ["#f5eddb", "#17222b", "#f06d38", "#0a6d83"], "pattern": 1},
    "gqom-inspired": {"title": "Gqom-Inspired Studies", "brief_name": "Gqom-inspired", "code": "gq", "bpm": 124, "root": 45, "mode": [0, 1, 3, 5, 7, 8, 10], "chord_steps": [0, 1, 5, 3], "intent": "Sparse low-register tension shaped by percussion and negative space.", "rhythm": "Low anchors leave intentional gaps while concise percussion cells answer at the edges.", "palette": "Low synthesized tones, dry percussion, exposed hook fragments and sparse upper texture.", "guardrail": "Inspired is a bounded production direction, not a claim of scene membership or authenticity.", "studies": ["Floor Signal", "Quiet Corner", "Black Tile", "Gap Return"], "colors": ["#efe8d7", "#101416", "#d6533f", "#5e8091"], "pattern": 2},
    "amapiano-inspired": {"title": "Amapiano-Inspired Studies", "brief_name": "Amapiano-inspired", "code": "ap", "bpm": 112, "root": 49, "mode": [0, 2, 3, 5, 7, 9, 10], "chord_steps": [0, 5, 2, 6], "intent": "Patient keyboard-led interplay and spacious bass/percussion dialogue.", "rhythm": "Patient key phrases converse with spacious bass entries and carefully reserved percussion.", "palette": "Warm keyboard cells, monophonic bass, light melodic lead and selective high texture.", "guardrail": "Inspired is a bounded production direction, not a cultural or historical claim.", "studies": ["Room Tone", "Slow Glass", "Seat Five", "Late Light"], "colors": ["#f4efd9", "#26342d", "#d9733d", "#397b77"], "pattern": 3},
    "kuduro-inspired": {"title": "Kuduro-Inspired Studies", "brief_name": "Kuduro-inspired", "code": "ku", "bpm": 140, "root": 52, "mode": [0, 2, 3, 5, 7, 9, 10], "chord_steps": [0, 4, 1, 5], "intent": "Sharp rhythmic exchange with concise, contrasting melodic gestures.", "rhythm": "Angular kick-and-answer cells trade with concise melodic interruptions.", "palette": "Hard-edged synth stabs, compact bass, narrow-range lead and dry percussion.", "guardrail": "Inspired is a bounded production direction and does not represent a community or history.", "studies": ["Edge Relay", "Turn Cell", "Wire Move", "Hard Return"], "colors": ["#f7eddf", "#1a1b2c", "#df5036", "#3d71a8"], "pattern": 4},
    "baile-funk-inspired": {"title": "Baile Funk-Inspired Studies", "brief_name": "Baile Funk-inspired", "code": "bf", "bpm": 132, "root": 46, "mode": [0, 2, 3, 5, 7, 8, 10], "chord_steps": [0, 5, 3, 1], "intent": "Percussion-forward original instrumentals with succinct rhythmic hooks.", "rhythm": "Original percussive hooks carry the phrase while bass and short lead gestures leave clear air.", "palette": "Synthetic percussion, low monophonic bass, clipped harmonic cells and a compact hook.", "guardrail": "No sampled vocals, copied breaks or claims to cultural authenticity.", "studies": ["Fader Heat", "Block Echo", "Signal Dash", "Warm Return"], "colors": ["#f6eddf", "#241a19", "#e55336", "#ac2f58"], "pattern": 5},
    "dembow-inspired": {"title": "Dembow-Inspired Studies", "brief_name": "Dembow-inspired", "code": "db", "bpm": 116, "root": 50, "mode": [0, 2, 3, 5, 7, 9, 10], "chord_steps": [0, 5, 1, 4], "intent": "Repetition with carefully composed syncopated variation.", "rhythm": "A repeated original anchor receives small deterministic syncopated variations across structural regions.", "palette": "Dry percussion, round bass, concise chord punches and an uncluttered melodic cell.", "guardrail": "Inspired is a limited arrangement direction, not a genre-defining or cultural claim.", "studies": ["Repeat Frame", "Small Turn", "Offset Loop", "Clear Exit"], "colors": ["#f6eedc", "#28221d", "#db613d", "#76811f"], "pattern": 6},
    "uk-funky-inspired": {"title": "UK Funky-Inspired Studies", "brief_name": "UK Funky-inspired", "code": "uf", "bpm": 128, "root": 53, "mode": [0, 2, 4, 5, 7, 9, 11], "chord_steps": [0, 4, 1, 5], "intent": "Interlocking rhythmic layers with a clear melodic center.", "rhythm": "Interlocking layers set a clear center while accents reposition from region to region.", "palette": "Rounded chord stabs, low bass, a single melodic focus and reserved counter texture.", "guardrail": "Inspired is a bounded writing prompt, not an authenticity or history claim.", "studies": ["Arc Light", "Centre Step", "Loose Thread", "Seven Return"], "colors": ["#f7f0df", "#172631", "#ec643d", "#187e90"], "pattern": 7},
    "broken-beat": {"title": "Broken Beat Studies", "brief_name": "Broken Beat", "code": "bb", "bpm": 118, "root": 50, "mode": [0, 2, 3, 5, 7, 9, 10], "chord_steps": [0, 3, 5, 1], "intent": "Off-center rhythmic conversation with harmonically purposeful writing.", "rhythm": "Off-center drum and bass answers leave room for harmonic turns to remain legible.", "palette": "Electric-keyboard-like chord colors, bass, focused lead and light percussion detail.", "guardrail": "The title identifies a production study, not a historical or cultural authority.", "studies": ["Bent Meter", "Paper Sync", "Near Miss", "True Return"], "colors": ["#f3ead8", "#20262a", "#dc5b46", "#7a6fa0"], "pattern": 8},
    "bossa-nova-inspired": {"title": "Bossa Nova-Inspired Studies", "brief_name": "Bossa Nova-inspired", "code": "bn", "bpm": 96, "root": 48, "mode": [0, 2, 4, 5, 7, 9, 11], "chord_steps": [0, 4, 1, 5], "intent": "Quiet original melodic phrasing and intimate harmonic response.", "rhythm": "Soft, deterministic accompaniment offsets frame quietly paced original melodic phrases.", "palette": "Nylon-like synth recipe, restrained bass, compact harmony and one clear melody.", "guardrail": "Inspired is a constrained writing direction; no cultural authenticity is claimed.", "studies": ["Window Plant", "Held Reply", "Soft Count", "Porch Return"], "colors": ["#f8f0dd", "#273433", "#d66d3d", "#5e9483"], "pattern": 9},
    "chamber-jazz": {"title": "Chamber Jazz Studies", "brief_name": "Chamber Jazz", "code": "cj", "bpm": 104, "root": 50, "mode": [0, 2, 3, 5, 7, 9, 10], "chord_steps": [0, 2, 5, 3], "intent": "Small-ensemble conversation with written motivic development.", "rhythm": "Written entries and rests establish small-ensemble conversation before transformed return.", "palette": "Piano-like harmony, bass, lead line, answer voice and quiet texture.", "guardrail": "Instrument names are synthesis directions only; MIDI data does not establish physical playability.", "studies": ["Four Chairs", "Paper Reed", "Answer Line", "Room Return"], "colors": ["#f4ecda", "#2d2731", "#bf573c", "#687e9d"], "pattern": 10},
    "post-rock": {"title": "Post-Rock Studies", "brief_name": "Post-rock", "code": "pr", "bpm": 108, "root": 45, "mode": [0, 2, 3, 5, 7, 8, 10], "chord_steps": [0, 5, 3, 6], "intent": "Slow-building instrumental narrative with thematic transformation.", "rhythm": "Sparse opening cells accumulate only at the statement and transformed-return regions.", "palette": "Sustained synthesized harmony, low bass, one melody, accent voice and texture.", "guardrail": "The studies are original MIDI arrangements, not recordings or a claim about a scene.", "studies": ["After the Rail", "Long Form", "Quiet Lift", "Open Return"], "colors": ["#f0e9dc", "#1d2934", "#db623f", "#416f98"], "pattern": 11},
    "shoegaze-inspired": {"title": "Shoegaze-Inspired Studies", "brief_name": "Shoegaze-inspired", "code": "sg", "bpm": 116, "root": 52, "mode": [0, 2, 4, 5, 7, 9, 11], "chord_steps": [0, 4, 5, 1], "intent": "A legible original melodic core inside layered harmonic texture.", "rhythm": "A legible melody is kept above layered but selectively entered harmonic texture.", "palette": "Wide synthesized chords, bass, clear top-line, small answering voice and texture.", "guardrail": "Inspired identifies a bounded production direction, not an authenticity claim.", "studies": ["Milk Glass", "Blur Field", "Open Chord", "White Return"], "colors": ["#f5eddf", "#252434", "#d95b55", "#7566a3"], "pattern": 12},
    "math-rock": {"title": "Math Rock Studies", "brief_name": "Math Rock", "code": "mr", "bpm": 132, "root": 50, "mode": [0, 2, 4, 6, 7, 9, 11], "chord_steps": [0, 2, 6, 4], "intent": "Interlocking original motifs with precise cross-accent design.", "rhythm": "Interlocking motifs move through precise cross-accent placements without randomization.", "palette": "Clean pluck synthesis, short bass, principal melody, answer voice and texture.", "guardrail": "The work is symbolic MIDI, not evidence of instrumental physical playability.", "studies": ["Bracket Form", "Five Against", "Glass Mark", "Thread Return"], "colors": ["#f6eedf", "#20272d", "#de5b37", "#16899d"], "pattern": 13},
    "djent-inspired": {"title": "Djent-Inspired Studies", "brief_name": "Djent-inspired", "code": "dj", "bpm": 144, "root": 38, "mode": [0, 1, 3, 5, 6, 8, 10], "chord_steps": [0, 1, 5, 3], "intent": "Controlled low-register rhythmic precision and melodic contrast.", "rhythm": "Low-register rhythmic cells are measured against shorter high melodic contrast.", "palette": "Synthesized low-string proxy, bass, compact lead, accent voice and texture.", "guardrail": "Instrument labels are sound-design recipes, not claims of performance feasibility.", "studies": ["Low Gate", "Iron Count", "Mute Grid", "Tight Return"], "colors": ["#efe8d9", "#1d2123", "#cf563c", "#617982"], "pattern": 14},
    "blackgaze-inspired": {"title": "Blackgaze-Inspired Studies", "brief_name": "Blackgaze-inspired", "code": "bg", "bpm": 168, "root": 43, "mode": [0, 2, 3, 5, 7, 8, 10], "chord_steps": [0, 3, 5, 1], "intent": "Original contrast between urgent texture and exposed melodic space.", "rhythm": "Urgent upper texture alternates with exposed melodic silence across defined sections.", "palette": "Layered synth texture, low support, clear lead, accent voice and dry percussion.", "guardrail": "Inspired is a bounded production direction; no cultural, scene or recording claim is made.", "studies": ["Weather Line", "Ash Field", "Bright Noise", "Long Return"], "colors": ["#f2ecdf", "#1c2530", "#cf5343", "#4b7895"], "pattern": 15},
    "sludge-metal": {"title": "Sludge Metal Studies", "brief_name": "Sludge Metal", "code": "sm", "bpm": 72, "root": 35, "mode": [0, 1, 3, 5, 6, 8, 10], "chord_steps": [0, 5, 1, 3], "intent": "Heavy original riff development through space, duration and contrast.", "rhythm": "Long low gestures are separated by deliberate space and short contrasting responses.", "palette": "Low synthesized riff proxy, bass, sparse melody, answer voice and texture.", "guardrail": "The title is a production study label; MIDI does not prove physical performance or recording process.", "studies": ["Weight Room", "Slow Mark", "Ground Shift", "Heavy Return"], "colors": ["#eee7da", "#2c2521", "#bd533b", "#92712f"], "pattern": 16},
    "dungeon-synth": {"title": "Dungeon Synth Studies", "brief_name": "Dungeon Synth", "code": "ds", "bpm": 76, "root": 45, "mode": [0, 1, 3, 5, 7, 8, 10], "chord_steps": [0, 5, 3, 1], "intent": "Original fictional-world miniatures with restrained thematic writing.", "rhythm": "Sparse pulse entries support restrained original themes and fictional-world scene changes.", "palette": "Monophonic bass, bell-like lead, soft harmonic cells, answer voice and air texture.", "guardrail": "Fictional-world framing is original and does not use or recreate copyrighted settings.", "studies": ["Stone Door", "Lantern Key", "Moss Hall", "North Return"], "colors": ["#f1ead8", "#202d2b", "#b85a3d", "#6f8c52"], "pattern": 17},
    "chiptune": {"title": "Chiptune Studies", "brief_name": "Chiptune", "code": "ct", "bpm": 148, "root": 48, "mode": [0, 2, 4, 5, 7, 9, 11], "chord_steps": [0, 4, 5, 1], "intent": "Original melodic clarity under an explicit voice budget.", "rhythm": "A deliberately limited voice budget keeps the original melody clear across changing cells.", "palette": "Pulse-wave recipe, bass, monophonic lead, small answer channel, sparse texture.", "guardrail": "No game recordings, character names, copied themes or platform affiliation claims are included.", "studies": ["Pixel Road", "Coin Window", "Clear Loop", "Start Return"], "colors": ["#f6edd8", "#1a2630", "#e05a3f", "#239477"], "pattern": 18},
    "electro-swing-inspired": {"title": "Electro Swing-Inspired Studies", "brief_name": "Electro Swing-inspired", "code": "es", "bpm": 124, "root": 50, "mode": [0, 2, 3, 5, 7, 9, 10], "chord_steps": [0, 3, 5, 1], "intent": "Newly composed melodic playfulness against an electronic arrangement.", "rhythm": "Original playful melody cells answer electronic percussion without sampled recordings.", "palette": "Short brass-like synthesis, bass, clear lead, answer voice and restrained texture.", "guardrail": "No sampled vintage recordings, quoted songs, artist likenesses or historical-authenticity claims.", "studies": ["Button Step", "Brass Paper", "Side Door", "Bright Return"], "colors": ["#f7efd9", "#2c2721", "#d85b39", "#95702f"], "pattern": 19},
    "cinematic-minimalism": {"title": "Cinematic Minimalism Studies", "brief_name": "Cinematic Minimalism", "code": "cm", "bpm": 88, "root": 50, "mode": [0, 2, 3, 5, 7, 8, 10], "chord_steps": [0, 5, 3, 1], "intent": "Original small-cell development across a clear dramatic arc.", "rhythm": "Small cells repeat with measured transformation over a transparent four-region dramatic arc.", "palette": "Piano-like synthesis, bass, clear lead, answer voice and low-density texture.", "guardrail": "Cinematic is an arrangement descriptor only, not a claim of synchronization or credits.", "studies": ["First Frame", "Held Line", "Distance Cue", "Final Return"], "colors": ["#f5eddf", "#212b35", "#d76347", "#507c9b"], "pattern": 20},
    "neurofunk-inspired": {"title": "Neurofunk-Inspired Studies", "brief_name": "Neurofunk-inspired", "code": "nf", "bpm": 172, "root": 38, "mode": [0, 1, 3, 5, 6, 8, 10], "chord_steps": [0, 1, 5, 3], "intent": "Original sharply articulated bass gestures within a fast rhythmic structure.", "rhythm": "Sharp original bass gestures are framed by fast but deterministic percussion positions.", "palette": "Articulated synth bass, clipped harmonic cells, concise lead, answer voice and texture.", "guardrail": "Inspired is a narrow production direction, not a claim of genre authority or membership.", "studies": ["Spine Cell", "Wire Bass", "Fast Shadow", "Cut Return"], "colors": ["#f1eade", "#1b2227", "#d95342", "#287d83"], "pattern": 21},
    "halftime-bass": {"title": "Halftime Bass Studies", "brief_name": "Halftime Bass", "code": "hb", "bpm": 168, "root": 41, "mode": [0, 2, 3, 5, 7, 8, 10], "chord_steps": [0, 5, 1, 3], "intent": "Spacious original low-end arrangements with a slower perceived phrase pace.", "rhythm": "Spacious low-end cells use a slow perceived phrase pace against exact fast-grid timing.", "palette": "Low bass, concise harmony, monophonic lead, sparse answer voice and texture.", "guardrail": "The title identifies a writing constraint, not a claim about a scene or recording practice.", "studies": ["Half Light", "Wide Floor", "Slow Signal", "Deep Return"], "colors": ["#f2ebdc", "#1d2930", "#d75e40", "#467d8b"], "pattern": 22},
}


def slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-").replace("--", "-")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def write_json(path: Path, data: object) -> None:
    path.write_bytes((json.dumps(data, indent=2) + "\n").encode("utf-8"))


def write_text(path: Path, value: str) -> None:
    """Write UTF-8 text with LF line endings on every host."""
    path.write_bytes(value.encode("utf-8"))


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def roles(pack: dict) -> list[tuple[str, str, int, int, int]]:
    return [
        ("chord_pulse", "Selective harmonic cells derived from: " + pack["palette"], 0, 1, 3),
        ("sub_bass", "Monophonic low-register anchor", 1, 2, 1),
        ("principal_motif", "Monophonic principal melody", 2, 3, 1),
        ("vocal_like_synth", "Selective answering voice", 3, 4, 1),
        ("counter_texture", "Selective two-note upper texture", 4, 5, 2),
        ("drums", "Original note-mapped percussion", 9, 10, 4),
    ]


def make_studies(pack: dict) -> list[dict]:
    out = []
    for index, title in enumerate(pack["studies"]):
        root = pack["root"] + (index * 3) % 8
        scale = pack["mode"]
        chord_roots = [root + step for step in pack["chord_steps"]]
        chords = [[chord_root, chord_root + scale[2], chord_root + scale[4]] for chord_root in chord_roots]
        motif = [72 + ((root + scale[(index + step) % len(scale)]) % 12) for step in (0, 2, 4, 3, 5, 1)]
        out.append({
            "id": f"{pack['code']}{index + 1:02d}", "slug": slugify(title), "title": title,
            "tonic": ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][root % 12],
            "collection": "pack-local equal-tempered pitch collection", "chords": chords,
            "bass": [chord_root - 24 for chord_root in chord_roots], "motif": motif,
            "voice": [motif[1] + 5, motif[3] + 2, motif[4] - 3, motif[2] + 4],
            "texture": [motif[0] - 5, motif[2] - 5, motif[4] - 5, motif[1] - 5],
            "pulses": [[120, 900, 1500], [0, 720, 1380], [240, 1020, 1620]][(pack["pattern"] + index) % 3],
            "motifs": [[300, 510, 810, 1110, 1410, 1650], [180, 480, 780, 1080, 1380, 1620], [120, 420, 900, 1200, 1500, 1680]][(pack["pattern"] + index) % 3],
            "intent": pack["intent"] + " " + ["Initial cell establishes the material.", "Statement introduces a different contour.", "Contrast moves the accent map.", "Return keeps the identity while changing one placement."][index],
        })
    return out


def region_name(bar: int) -> str:
    for key, _, start, length in SECTIONS:
        if start <= bar < start + length:
            return key
    raise ValueError("invalid bar")


def add(score: dict[str, list[dict]], role: str, start: int, pitch: int, duration: int, velocity: int, ornament: bool = False) -> None:
    score[role].append(engine.note(start, engine.ROLE[role][2], pitch, duration, velocity, ornament))


def compose(study: dict, study_index: int, pattern: int) -> dict[str, list[dict]]:
    score = {role: [] for role in ROLE_NAMES}
    bass_offsets = [[0, 780, 1440], [0, 600, 1320], [0, 960, 1560]][pattern % 3]
    drum_cells = [[0, 720, 1320], [0, 540, 1200, 1560], [0, 840, 1440]][pattern % 3]
    for bar in range(BARS):
        base, section = bar * BAR_TICKS, region_name(bar)
        chord_index = (bar // 4 + study_index) % 4
        chord = study["chords"][chord_index]
        if not (section == "introduction" and bar % 2):
            for ordinal, offset in enumerate(study["pulses"]):
                if section == "contrast" and ordinal == 1:
                    continue
                for pitch in chord:
                    add(score, "chord_pulse", base + offset, pitch, 180 if ordinal != 2 else 240, 64 + ordinal * 8)
        for ordinal, offset in enumerate(bass_offsets):
            if section == "introduction" and ordinal == 1:
                continue
            shift = 60 if section == "transformed_return" and ordinal == 2 else 0
            add(score, "sub_bass", base + offset + shift, study["bass"][chord_index] + (12 if ordinal == 2 else 0), 210, 84 + ordinal * 6)
        if section != "introduction" or bar >= 4:
            for ordinal, offset in enumerate(study["motifs"]):
                if section == "contrast" and ordinal in (1, 4):
                    continue
                pitch = study["motif"][(ordinal + bar + (1 if section == "transformed_return" else 0)) % len(study["motif"])]
                duration = 150 if ordinal % 3 else 210
                add(score, "principal_motif", base + offset, pitch, duration, 74 + (ordinal % 3) * 8)
                if ordinal == 2 and section in ("statement", "transformed_return"):
                    add(score, "principal_motif", base + offset + duration, pitch + 2, 45, 52, True)
        if section in ("statement", "transformed_return") and bar % 2:
            for ordinal, offset in enumerate((360, 1080)):
                add(score, "vocal_like_synth", base + offset, study["voice"][(bar + ordinal) % 4], 150, 60 + ordinal * 9)
        if section in ("contrast", "transformed_return") and bar % 2 == 0:
            offset = 1260 if section == "contrast" else 1080
            pitch = study["texture"][(bar // 2) % 4]
            add(score, "counter_texture", base + offset, pitch, 270, 48)
            add(score, "counter_texture", base + offset, pitch + 7, 270, 43)
        for ordinal, offset in enumerate(drum_cells):
            if section == "contrast" and ordinal == 1:
                continue
            add(score, "drums", base + offset, 36, 60, 104 - ordinal * 7)
        for ordinal, offset in enumerate((480, 1260) if bar % 2 == 0 else (600, 1380)):
            add(score, "drums", base + offset, 38, 60, 87 + ordinal * 5)
            if section in ("statement", "transformed_return") and ordinal == 1:
                add(score, "drums", base + offset + 60, 39, 45, 62)
        for offset in range(240, BAR_TICKS, 240):
            if section == "introduction" and bar < 4 and offset in (720, 1200):
                continue
            if section == "contrast" and (offset // 240 + bar) % 3 == 0:
                continue
            add(score, "drums", base + offset, 42, 36, 45 + (bar + offset // 240) % 3 * 7)
        if bar in (7, 15, 23, 31):
            add(score, "drums", base + 1500, 46, 150, 60)
            add(score, "drums", base + 1680, 46, 30, 62)
    return score


def write_csvs(root: Path, pack: dict, studies: list[dict], scores: dict[str, dict[str, list[dict]]]) -> list[Path]:
    catalog = root / "catalog"
    outputs = []
    def emit(name: str, fields: list[str], rows: list[dict]) -> None:
        path = catalog / name
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)
        outputs.append(path)
    emit("study-index.csv", ["study_id", "title", "collection", "tonic", "tempo_bpm", "meter", "ppq", "bars", "end_tick", "combined_path", "roles"], [
        {"study_id": s["id"], "title": s["title"], "collection": s["collection"], "tonic": s["tonic"], "tempo_bpm": pack["bpm"], "meter": "4/4", "ppq": PPQ, "bars": BARS, "end_tick": END_TICK, "combined_path": f"midi/{s['id']}-{s['slug']}/{s['id']}-{s['slug']}-combined.mid", "roles": "; ".join(ROLE_NAMES)} for s in studies])
    note_rows = []
    for s in studies:
        for role, _, _, display, _ in engine.ROLES:
            for event in sorted(scores[s["id"]][role], key=lambda item: (item["start"], item["pitch"])):
                note_rows.append({"study_id": s["id"], "role": role, "user_facing_channel": display, "start_tick": event["start"], "duration_tick": event["duration"], "pitch": event["pitch"], "velocity": event["velocity"], "ornament": str(event["ornament"]).lower()})
    emit("note-events.csv", ["study_id", "role", "user_facing_channel", "start_tick", "duration_tick", "pitch", "velocity", "ornament"], note_rows)
    emit("structural-regions.csv", ["study_id", "region", "display_name", "start_bar", "bars", "start_tick", "end_tick"], [{"study_id": s["id"], "region": key, "display_name": label, "start_bar": start + 1, "bars": length, "start_tick": start * BAR_TICKS, "end_tick": (start + length) * BAR_TICKS} for s in studies for key, label, start, length in SECTIONS])
    emit("harmonic-events.csv", ["study_id", "bar", "start_tick", "tonic", "collection", "chord_pitches", "intent"], [{"study_id": s["id"], "bar": bar + 1, "start_tick": bar * BAR_TICKS, "tonic": s["tonic"], "collection": s["collection"], "chord_pitches": " ".join(str(p) for p in s["chords"][(bar // 4 + index) % 4]), "intent": s["intent"]} for index, s in enumerate(studies) for bar in range(BARS)])
    emit("drum-map.csv", ["midi_pitch", "name", "purpose"], [{"midi_pitch": row["pitch"], "name": row["name"], "purpose": row["purpose"]} for row in DRUM_MAP])
    recipes = {"renderer": "release-simple-synth 1.0.0", "midi_policy": "No program changes, controllers, pitch bends, keyswitches, SysEx or sampled audio are encoded in the MIDI.", "gm_fallback": "Mappings are not encoded; a generic player will substitute its own sounds.", "roles": [{"role": role, "description": description, "wire_channel": wire, "user_facing_channel": display, "polyphony_cap": cap} for role, description, wire, display, cap in engine.ROLES], "gain_stages": {"role_target": "approximately -20 dBFS before summing", "master_processing": "none", "loudness_claim": "none"}}
    recipe_path = catalog / "patch-recipes.json"; write_json(recipe_path, recipes); outputs.append(recipe_path)
    return outputs


def write_release_spec(root: Path, pack: dict, studies: list[dict]) -> Path:
    path = root / "catalog" / "release-spec.json"
    write_json(path, {"pack_identifier": pack["slug"], "display_name": pack["title"], "brief_name": pack["brief_name"], "creative_intention": pack["intent"], "rhythmic_direction": pack["rhythm"], "palette": pack["palette"], "guardrail": pack["guardrail"], "generator_version": "release-train-1.0.0", "reproducible_command": f"python tools/build_release.py --pack {pack['slug']}", "actual_tempo_bpm": pack["bpm"], "meter": "4/4", "ppq": PPQ, "end_tick": END_TICK, "roles": [{"role": r, "wire_channel": w, "user_facing_channel": d, "polyphony_cap": cap} for r, _, w, d, cap in engine.ROLES], "studies": [{"id": s["id"], "title": s["title"], "tonic": s["tonic"], "pitch_collection": s["collection"]} for s in studies], "limitations": ["Original symbolic material; no samples.", "Automated validation is technical evidence, not copyright clearance.", "The listening file is a simple-synthesis preview, not a master."]})
    return path


def make_zip(root: Path, pack: dict, parts: list[Path], combined: list[Path], metadata: list[Path]) -> Path:
    archive = root / "downloads" / f"{pack['slug']}-midi.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path in parts + combined + metadata:
            output.write(path, rel(root, path))
    return archive


def write_cover(root: Path, pack: dict) -> Path:
    bg, ink, accent, blue = pack["colors"]
    path = root / "art" / "cover.svg"
    cells = "".join(f'<rect x="{80 + (i % 4) * 170}" y="{140 + (i // 4) * 138 + ((i + pack["pattern"]) % 2) * 28}" width="{82 + (i % 3) * 23}" height="24" fill="{accent if i % 2 else blue}" opacity="{.62 + (i % 3) * .12}"/>' for i in range(12))
    write_text(path, f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 760" role="img" aria-labelledby="t d"><title id="t">{pack["title"]} cover</title><desc id="d">Original geometric score illustration with staggered rhythmic cells.</desc><rect width="1200" height="760" fill="{bg}"/><path d="M0 122H1200M0 300H1200M0 478H1200M0 656H1200" stroke="{ink}" opacity=".16"/><path d="M70 0V760M240 0V760M410 0V760M580 0V760M750 0V760M920 0V760M1090 0V760" stroke="{ink}" opacity=".12"/>{cells}<path d="M65 590 C235 475 320 655 488 545 S805 405 1135 525" fill="none" stroke="{ink}" stroke-width="11"/><text x="72" y="88" fill="{ink}" font-family="Arial,Helvetica,sans-serif" font-size="30" letter-spacing="6">ORIGINAL MIDI STUDIES</text><text x="72" y="695" fill="{ink}" font-family="Georgia,serif" font-size="88">{pack["brief_name"]}</text><text x="76" y="732" fill="{ink}" font-family="Arial,Helvetica,sans-serif" font-size="24" letter-spacing="3">{pack["bpm"]} BPM · FOUR STUDIES · 32 BARS EACH</text></svg>''')
    write_json(root / "art" / "cover-provenance.json", {"asset": "art/cover.svg", "classification": "Original programmatic abstract illustration; not a photograph, session record or instrument claim.", "construction": "SVG rhythmic-cell composition generated from the pack profile; no external images or logos."})
    return path


def write_preview(root: Path, pack: dict, combined: Path) -> Path:
    source, manifest = engine.render_preview(combined)
    target = root / "preview" / f"{pack['slug']}-simple-synth-preview.mp3"
    source.replace(target)
    (root / "preview" / "preview-manifest-Codex.json").unlink(missing_ok=True)
    manifest["preview_path"] = rel(root, target); manifest["preview_sha256"] = digest(target); manifest["renderer"] = "release-simple-synth 1.0.0"; manifest["selection"]["study"] = pack["code"] + "01"; manifest["limitations"] = "Automated generation and decode checks only. Nobody auditioned this simple-synthesis preview. It is not a finished-production sound or master."
    write_json(root / "preview" / "preview-manifest.json", manifest)
    return target


def write_drafts(root: Path, pack: dict) -> None:
    article = f"""# DRAFT — {pack['title']}

## A bounded symbolic-MIDI collection

{pack['title']} contains four original {pack['bpm']} BPM studies. {pack['intent']} The collection documents timing, role assignment, structural regions and synthesis recipes rather than asserting a definitive account of a genre or community.

Tags: MIDI, composition, music production, synthesis

The listening file is generated from committed MIDI events with a simple synthesizer. It is a preview, not a master. Automated validation reopened the exported files; nobody auditioned these files.

Call to action: inspect the catalog and validation record before downloading the MIDI archive.
"""
    write_text(root / "articles" / "medium-draft.md", article)
    instagram = f"DRAFT. {pack['title']}: four original {pack['bpm']} BPM MIDI studies. {pack['intent']} Simple-synthesis preview, not a master. #MIDI #musicproduction #composition\n\nAlt text: abstract staggered rhythmic cells on a structured grid.\n"
    write_text(root / "social" / "instagram" / "caption.txt", instagram)
    post = f"DRAFT: {pack['title']} is a four-study original MIDI release at {pack['bpm']} BPM. Simple-synthesis preview, not a master. #MIDI #Composition"
    if len(post) > 280: raise ValueError("X post exceeds 280 characters")
    write_text(root / "social" / "x" / "post.txt", post + f"\n\nCount: {len(post)} characters using Python len\n")


def write_documents(root: Path, pack: dict, studies: list[dict]) -> None:
    study_rows = "\n".join(f"| {s['id']} {s['title']} | {s['tonic']} pack-local pitch collection | 32 bars · {pack['bpm']} BPM · 4/4 |" for s in studies)
    readme = f"""# {pack['title']}

Four original note-only MIDI studies for producers who need the musical structure documented as carefully as the files.

**Live catalog:** https://mizcausevic-dev.github.io/{pack['slug']}/

This is a bounded symbolic-composition release, not a sample pack, recording, or claim to define a genre, its history or its communities.

## The studies

| Study | Pitch collection | Frame |
| --- | --- | --- |
{study_rows}

The release contains 28 MIDI files: six Format 0 role exports and one Format 1 combined arrangement per study. It also contains canonical event CSVs, structural/harmonic/drum-map records, patch recipes, checksums, an original SVG cover, a simple-synthesis preview, draft editorial copy and one ZIP.

## Start here

1. Open the live catalog or download `downloads/{pack['slug']}-midi.zip`.
2. Choose either a combined arrangement or the separate part files. **Do not stack the part files on the combined file.**
3. Read `catalog/patch-recipes.json` for channel/role mappings, and `checks/validation-report.json` before relying on a technical claim.

## File contract

- 480 PPQ, 4/4, {pack['bpm']} BPM, 61,440 end ticks per study.
- Five pitched roles use user-facing channels 1–5 (wire values 0–4); drums use user-facing channel 10 (wire value 9).
- Bass and principal melody are monophonic. No program changes, controllers, pitch bends, keyswitches or SysEx are present.
- {pack['guardrail']}

## Technical verification boundary

The validator reopens final bytes and checks MIDI count, Format 0/1 shape, PPQ, tempo, meter, named combined tracks, event timing, note pairing, role channels, monophony, same-pitch overlap, CSV parity, region coverage, drum-map coverage, ZIP paths, preview decode and checksum records. It also runs a known-invalid same-pitch-overlap fixture.

It does **not** certify groove, musical quality, commercial suitability, physical playability, cultural authenticity or copyright clearance. Duplicate-motif results are only a bounded structural review. Automated checks may pass while human listening remains unperformed.

The preview is generated from the first study's committed MIDI with a documented simple synthesizer. It is a **preview, not a master**.

## Rebuild

```powershell
python tools/build_release.py --pack {pack['slug']}
python tools/validate_release.py
python -m http.server 4173
```

`tools/build_footwork.py` is the local MIDI byte engine retained from the initial release; `tools/build_release.py` is the profile-driven release writer. The committed outputs, rather than an external service, are the build evidence.
"""
    write_text(root / "README.md", readme)
    write_text(root / "delivery.md", f"# {pack['title']} delivery record\n\n- Repository target: `mizcausevic-dev/{pack['slug']}`\n- GitHub Pages source: `main` branch, repository root\n- Expected public catalog: `https://mizcausevic-dev.github.io/{pack['slug']}/`\n- Local build evidence: `checks/validation-report.json`\n- Limitation: automated technical validation is not listening review, copyright clearance or production-master evidence.\n")


def write_site(root: Path, pack: dict, studies: list[dict], archive: Path, preview: Path) -> None:
    bg, ink, accent, blue = pack["colors"]
    cards = "".join(f'<article class="study"><p class="code">{s["id"]}</p><h3>{s["title"]}</h3><p>{s["intent"]}</p><a href="midi/{s["id"]}-{s["slug"]}/{s["id"]}-{s["slug"]}-combined.mid">Open combined MIDI</a></article>' for s in studies)
    roles_html = "".join(f'<li><b>ch {display}</b> {description}</li>' for _, description, _, display, _ in engine.ROLES)
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{pack['title']}: four original {pack['bpm']} BPM MIDI studies with event catalog and validation record."><meta property="og:title" content="{pack['title']}"><meta property="og:description" content="Original MIDI studies with a public event catalog and validation record."><title>{pack['title']} | Original MIDI studies</title><style>
:root{{--paper:{bg};--ink:{ink};--accent:{accent};--blue:{blue};--line:color-mix(in srgb,var(--ink) 22%,transparent)}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:17px/1.5 ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif}}a{{color:inherit;text-underline-offset:.18em;text-decoration-thickness:2px}}a:focus-visible{{outline:3px solid var(--blue);outline-offset:4px}}.wrap{{width:min(1180px,calc(100% - 32px));margin:auto}}nav{{display:flex;justify-content:space-between;gap:16px;align-items:center;padding:20px 0;border-bottom:1px solid var(--line);font-size:.87rem;letter-spacing:.08em;text-transform:uppercase}}nav .links{{display:flex;flex-wrap:wrap;gap:14px}}.hero{{display:grid;grid-template-columns:1.05fr .95fr;gap:36px;align-items:end;padding:65px 0 42px;border-bottom:1px solid var(--line)}}.eyebrow,.code{{font-size:.78rem;letter-spacing:.16em;text-transform:uppercase;font-weight:800}}.eyebrow{{color:var(--accent)}}h1{{font:clamp(4.1rem,9vw,9.6rem)/.78 Georgia,serif;letter-spacing:-.075em;margin:.35rem 0 1.4rem;max-width:8ch}}h2{{font:clamp(2.4rem,5vw,4.6rem)/.92 Georgia,serif;letter-spacing:-.05em;margin:.3rem 0 1rem}}h3{{font:1.55rem/1.05 Georgia,serif;margin:.25rem 0 .65rem}}.lede{{font-size:1.18rem;max-width:48ch}}.actions{{display:flex;flex-wrap:wrap;gap:14px;margin-top:28px}}.button{{display:inline-block;background:var(--ink);color:var(--paper);padding:13px 16px;text-decoration:none;font-weight:800;border-radius:2px}}.button.alt{{background:var(--accent);color:var(--ink)}}.cover{{border:1px solid var(--line);box-shadow:14px 14px 0 var(--blue)}}.cover img{{width:100%;display:block}}section{{padding:66px 0;border-bottom:1px solid var(--line)}}.twocol{{display:grid;grid-template-columns:1fr 1fr;gap:36px}}.note{{border-left:6px solid var(--accent);padding:8px 0 8px 20px;max-width:58ch}}.study-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:0;border:1px solid var(--line)}}.study{{padding:20px;border-right:1px solid var(--line);min-height:255px}}.study:last-child{{border-right:0}}.study p{{font-size:.92rem}}.study a{{font-weight:800}}.proof{{display:grid;grid-template-columns:1fr 1.15fr;gap:34px;align-items:start}}audio{{width:100%;accent-color:var(--accent)}}.spec{{margin:0;padding:0;list-style:none;border-top:1px solid var(--line)}}.spec li{{padding:13px 0;border-bottom:1px solid var(--line)}}.spec b{{color:var(--accent);display:inline-block;width:68px}}.catalog{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}.catalog a{{padding:18px;border:1px solid var(--line);font-weight:800;text-decoration:none}}.catalog a:hover{{background:var(--ink);color:var(--paper)}}footer{{padding:40px 0 70px;font-size:.92rem;max-width:76ch}}@media(max-width:760px){{.hero,.twocol,.proof{{grid-template-columns:1fr;gap:25px}}h1{{font-size:clamp(3.5rem,21vw,6.5rem)}}.study-grid,.catalog{{grid-template-columns:1fr 1fr}}.study{{border-bottom:1px solid var(--line)}}.study:nth-child(2){{border-right:0}}.study:last-child{{border-right:0}}}}@media(max-width:430px){{.study-grid,.catalog{{grid-template-columns:1fr}}.study{{border-right:0}}nav{{align-items:flex-start;flex-direction:column}}}}
</style></head><body><div class="wrap"><nav aria-label="Main navigation"><a href="#top">{pack['title']}</a><div class="links"><a href="#studies">studies</a><a href="#evidence">evidence</a><a href="#catalog">catalog</a></div></nav><main id="top"><section class="hero"><div><p class="eyebrow">Original symbolic composition · four study release</p><h1>{pack['brief_name']}</h1><p class="lede">{pack['intent']} Four original {pack['bpm']} BPM scores built for inspection, arrangement and adaptation.</p><div class="actions"><a class="button" href="{rel(root, archive)}">Download 28-MIDI archive</a><a class="button alt" href="#evidence">Listen to source preview</a></div></div><div class="cover"><img src="art/cover.svg" width="1200" height="760" alt="Original geometric cover with staggered rhythmic cells on a structured grid."></div></section><section><div class="twocol"><div><p class="eyebrow">Composer's frame</p><h2>A score you can trace.</h2></div><div><p>{pack['rhythm']}</p><p>{pack['palette']}</p><p class="note">{pack['guardrail']}</p></div></div></section><section id="studies"><p class="eyebrow">The four studies</p><h2>Same contract. Different material.</h2><div class="study-grid">{cards}</div></section><section id="evidence" class="proof"><div><p class="eyebrow">Canonical listening file</p><h2>Timing, not a master.</h2><audio controls preload="metadata"><source src="{rel(root, preview)}" type="audio/mpeg"></audio><p>Generated from the first combined MIDI with the committed simple synthesizer. It was not auditioned and makes no finished-production claim.</p><p><a href="preview/preview-manifest.json">Open source and renderer manifest</a></p></div><div><p class="eyebrow">Playback roles</p><ul class="spec">{roles_html}</ul><p>Five musical roles are mapped to user-facing channels 1–5; drums use user-facing channel 10. Bass and principal melody are monophonic. No playback programs, controllers, pitch bends, keyswitches or SysEx are encoded.</p></div></section><section id="catalog"><p class="eyebrow">Evidence shelf</p><h2>Open the records.</h2><div class="catalog"><a href="catalog/release-spec.json">Release specification</a><a href="catalog/note-events.csv">Canonical note events</a><a href="catalog/study-index.csv">Study index</a><a href="catalog/structural-regions.csv">Structural regions</a><a href="catalog/harmonic-events.csv">Harmonic events</a><a href="catalog/drum-map.csv">Drum map</a><a href="catalog/patch-recipes.json">Patch recipes</a><a href="checks/validation-report.json">Validation report</a><a href="catalog/checksums.json">Checksum manifest</a></div></section><section><div class="twocol"><div><p class="eyebrow">Use note</p><h2>One arrangement at a time.</h2><p>Use the combined arrangement or its six separate role files. Do not stack both together.</p></div><div><p class="eyebrow">Review boundary</p><p>Automated checks validate exported-file integrity, not groove, cultural framing, commercial suitability, physical playability or copyright clearance. The duplicate-motif review is bounded structural analysis, not exhaustive clearance.</p><p>Draft promotional text is present in the repository only. Nothing is posted externally.</p></div></div></section></main><footer>Original MIDI studies. No samples, endorsements, artist likenesses, recorded performances or cultural-authenticity claims. <a href="README.md">Read the release notes</a> · <a href="delivery.md">delivery record</a>.</footer></div></body></html>'''
    write_text(root / "index.html", html)
    write_text(root / ".nojekyll", "")


def write_checksums(root: Path) -> None:
    skip = {"catalog/checksums.json", "checks/validation-report.json"}
    records = [{"path": rel(root, path), "bytes": path.stat().st_size, "sha256": digest(path)} for path in sorted(root.rglob("*")) if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts and rel(root, path) not in skip]
    write_json(root / "catalog" / "checksums.json", {"algorithm": "SHA-256", "files": records})


def configure(root: Path, pack: dict) -> list[dict]:
    engine.ROOT = root; engine.BPM = pack["bpm"]; engine.TEMPO_US = round(60_000_000 / pack["bpm"]); engine.VERSION = "release-train-1.0.0"
    engine.ROLES = roles(pack); engine.ROLE = {item[0]: item for item in engine.ROLES}; engine.DRUM_MAP = DRUM_MAP
    engine.STUDIES = make_studies(pack)
    return engine.STUDIES


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", choices=sorted(PACKS), required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(); root = args.root.resolve(); pack = dict(PACKS[args.pack]); pack["slug"] = args.pack
    for name in ("midi", "preview", "film", "art", "social", "articles", "catalog", "checks", "downloads", "docs"):
        shutil.rmtree(root / name, ignore_errors=True)
    for name in ("midi", "preview", "art", "social/instagram", "social/x", "articles", "catalog", "checks/fixtures", "downloads"):
        (root / name).mkdir(parents=True, exist_ok=True)
    studies = configure(root, pack); scores, parts, combined = {}, [], []
    for index, study in enumerate(studies):
        score = compose(study, index, pack["pattern"]); engine.assert_score(score); scores[study["id"]] = score
        role_files, combined_file = engine.write_midi(study, score); parts.extend(role_files); combined.append(combined_file)
    metadata = write_csvs(root, pack, studies, scores); metadata.append(write_release_spec(root, pack, studies))
    archive = make_zip(root, pack, parts, combined, metadata)
    preview = write_preview(root, pack, combined[0]); write_cover(root, pack); write_drafts(root, pack); write_documents(root, pack, studies); write_site(root, pack, studies, archive, preview)
    write_json(root / "checks" / "build-metadata.json", {"generator_version": "release-train-1.0.0", "pack": args.pack, "source_builder_sha256": digest(Path(__file__)), "commands": [f"python tools/build_release.py --pack {args.pack}", "python tools/validate_release.py"], "run_time_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version.split()[0]})
    subprocess.run([sys.executable, str(root / "tools" / "validate_release.py"), "--root", str(root)], check=True)
    write_checksums(root)
    subprocess.run([sys.executable, str(root / "tools" / "validate_release.py"), "--root", str(root)], check=True)
    print(json.dumps({"status": "generated", "pack": args.pack, "midi_files": len(parts) + len(combined), "archive": rel(root, archive), "preview": rel(root, preview)}, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
