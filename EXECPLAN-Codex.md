# Footwork Codex release plan

## Goal

Create one complete, original Footwork study pack and publish its file-catalog site to a new public GitHub repository at `mizcausevic-dev/footwork-codex`, served by GitHub Pages. The catalog must link real, validated downloadable MIDI, an honest preview, a short captioned film, raster art, draft publicity assets, and provenance.

## Current state

- **Observed:** `C:\Users\chaus\Documents\Codex\2026-11-03\th` is a generated task workspace, not a Git repository.
- **Observed:** GitHub access is available for `mizcausevic-dev` with repository write permission.
- **Observed:** The Footwork brief calls for four original 32-bar, 160 BPM, 4/4 studies, PPQ 480, exact 61,440-tick endings; five pitched roles on MIDI wire channels 0–4 and drums on channel 9; 28 MIDI exports plus catalog, CSVs, recipes, reports, ZIP, audio, video, art, and drafts.
- **Observed:** `ffmpeg` 8.1.2, `ffprobe` 8.1.2, and Python 3.14 are available. No existing Footwork repository or source folder was found.

## Scope

Included:

- A deterministic standard-library Python builder and validator.
- Four original studies, 24 Format 0 role files and four Format 1 combined files.
- MP3 preview rendered from study 01's committed combined MIDI event data using a documented simple synthesizer.
- 10–40 second MP4 film, WebVTT captions, 1280×720 hero JPG, square JPG, social derivations, article drafts, ZIP, catalog, checksum manifests, and static catalog site.
- GitHub repository creation, commit, Pages enablement, and live-byte/link verification.

Excluded:

- Claims of human listening, commercial mastering, cultural authority, sampled material, or public social/article publication.
- Recovering or overwriting the nine unrelated public scaffold repositories whose local source is unavailable.
- Building the remaining briefs before this pack has a validated live release.

## Acceptance criteria

- 28 parseable MIDI files reopen from final on-disk bytes; each ends at tick 61,440, contains correct tempo and meter, uses only permitted channels, and has valid note pairs.
- Role and score consistency, monophonic bass/principal melody, same-pitch non-overlap, file hashes, archive safety, and negative validation control are reported as passed.
- The preview MP3 is decodable and its source MIDI hash, renderer settings, excerpt, and output hash are in `preview/preview-manifest.json`.
- The film has both video and audio streams, is 10–40 seconds, links an in-duration VTT, and exposes the exact disclosure `preview, not a master` on-picture and in captions.
- Raster images decode at 1280×720 and 1080×1080. Social images derive from the square image and are 1080×1080 and 1080×1350.
- The static catalog makes only verified file claims, serves the actual media and downloads using relative paths, and labels articles/social material DRAFT.
- Remote commit/tree checks match local SHA-256 manifests and GitHub Pages serves the catalog successfully.

## Risks and release class

Release class: **R2** (public static release with downloadable creative assets).

- Copyright/creative risk: mitigate with original deterministic scores, no samples, and no genre-credential claims.
- Quality risk: automation establishes correctness and decodeability, not subjective audition quality; disclose this explicitly.
- Public-data risk: do not expose local paths, private repository names, credentials, or unsupported financial/endorsement claims.
- Platform risk: GitHub Pages is public and asynchronous; verify served files after deployment. Roll back by disabling Pages or reverting the release commit.

## Design

`tools/build_footwork.py` is the single deterministic source. It writes symbolic scores to MIDI and CSV, renders a simple-synth WAV/MP3 directly from the same selected MIDI event set, produces the MP4/VTT with ffmpeg, emits artifact records and checksums, and writes an accessible static catalog. `tools/validate_footwork.py` reopens written files and archive members independently.

The five musical roles are chord pulse, sub bass, principal motif, vocal-like synth lead, and counter texture. Drums are separate. No GM program changes are encoded; the renderer mapping is documented and any generic player falls back to its own default sound.

## Execution sequence

1. Add deterministic composition, MIDI writer/parser, renderer, validators, and static catalog generator.
2. Generate final deliverables and inspect media metadata/checksums.
3. Generate original illustration artwork; scale/crop it to required raster variants and register its provenance.
4. Run the validator, archive read-back, file/link checks, static-page browser checks, and a negative fixture.
5. Create `mizcausevic-dev/footwork-codex`, commit the reviewed final artifact tree to `main`, enable Pages from `main`/root, and verify the live site.
6. Record the actual repository URL, commit, Pages source, live URL, checksums, and residual limits in `delivery-codex.md`.

## Verification

- `python tools/build_footwork.py`
- `python tools/validate_footwork.py --root .`
- `ffprobe` stream/duration checks for preview and film.
- SHA-256 manifest recomputation.
- `python -m http.server` plus browser checks of page, download links, media, captions, mobile and desktop layout.
- Remote GitHub tree/commit read-back and public GitHub Pages HTTP checks.

## Deployment and rollback

Target: `https://github.com/mizcausevic-dev/footwork-codex`, GitHub Pages from `main` at repository root; expected live route `https://mizcausevic-dev.github.io/footwork-codex/`.

Prerequisite: final local validation and review. Deploy by committing the proven asset tree and enabling Pages. Verify the live home page and selected assets. Roll back by restoring the immediately prior `main` commit; for urgent removal, disable Pages in repository settings.

## Progress

- [x] 2026-11-03: GitHub access, local toolchain, source availability, and release risks inspected.
- [ ] Compose/build Footwork artifacts.
- [ ] Create artwork and social derivatives.
- [ ] Validate final bytes and browser behavior.
- [ ] Publish and verify GitHub Pages.

## Decisions

- Start with Footwork, the first brief, rather than fabricate completion across the remaining packs.
- Use `footwork-codex` to avoid colliding with any future pre-existing `footwork` repository.
- Treat `160 BPM` and the creative direction as project constraints only, not definitions of a music community or genre.

## Outcome

Pending execution.
