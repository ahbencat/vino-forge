# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project layout

This is the VinoForge monorepo — a series of OpenVINO-accelerated applications.

- `libs/ov_kit/` — shared: repository paths, device enumeration.
- `apps/vino-sub-gen/` — video/audio subtitle generation & translation (Whisper + Hy-MT2).
  - `apps/vino-sub-gen/lib/` — ASR, translation, timestamp modules.
  - `apps/vino-sub-gen/script/` — CLI entry points, batch driver, one-shot pipeline.
  - `apps/vino-sub-gen/gui/` — PySide6 desktop GUI.
  - `apps/vino-sub-gen/tool/model_conversion/` — OpenVINO model conversion utilities.
- `models/` — shared model cards and locally downloaded weights (not committed).

The project uses Python 3.10, OpenVINO/Optimum Intel, Whisper Large-v3, Silero VAD, and Hy-MT2. Shared repository-relative paths are defined in `libs/ov_kit/paths.py`.

## Common commands

Run from the repository root:

```bash
python -m py_compile libs/ov_kit/*.py apps/vino-sub-gen/lib/*.py apps/vino-sub-gen/script/*.py apps/vino-sub-gen/gui/*.py apps/vino-sub-gen/tool/model_conversion/*.py
python apps/vino-sub-gen/script/batch_generate.py "./videos" --dry-run
python apps/vino-sub-gen/script/generate_and_translate.py "input.mkv"
python apps/vino-sub-gen/gui/gui_app.py
```

For a single pipeline stage, use `python apps/vino-sub-gen/script/video_to_subtitle.py --help` or `python apps/vino-sub-gen/script/translate_srt.py --help`. The GUI requires the optional `PySide6` dependency. Video processing requires `ffmpeg` on `PATH`, or an `FFMPEG_PATH` environment variable.

## Release and publishing notes

There is currently no release script or CI release workflow in this repository. Do not assume that a source-code reorganization alone defines a distributable package; decide and verify the release artifacts for this Python project before publishing.

### Git push (SSH)

`origin` is `git@github.com:ahbencat/openvino_gen_sub.git`. Push and tag over SSH — no token, no proxy:

```bash
git push origin main        # or: git push origin main vX.Y.Z
```

The HTTPS URL will prompt for GitHub credentials instead; do not switch back to it.

### GitHub Release via gh (reference)

The adjacent project `D:/Projects/md-view-win/md-view-win/docs/release.md` documents this method. Summary only — adapt artifacts to this repo:

1. Commit, tag (`vX.Y.Z`), push over SSH as above.
2. Create the release with `gh`, reading the token inline so it never appears literally (strip CRLF; proxy `api.github.com` through the `cn_proxy` skill's `assets/proxy.json`):

```sh
GH_TOKEN="$(tr -d '\r\n' < ~/.config/git/git_token)" \
HTTP_PROXY=http://<proxy-host>:<proxy-port> \
HTTPS_PROXY=http://<proxy-host>:<proxy-port> \
gh release create vX.Y.Z \
  --repo ahbencat/openvino_gen_sub \
  --title "vX.Y.Z" \
  --notes-file <release-notes.md> \
  <artifact files...>
```

3. Never print, echo, log, or commit the token. If exposed, revoke it at https://github.com/settings/tokens, reissue, and update `C:\Users\Ahben\.config\git\git_token`.
4. Release notes go in a file (`--notes-file`), never inline long strings. Verify with `gh release view vX.Y.Z --json assets,tagName`.
