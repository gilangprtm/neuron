"""Vault Sync — scans local markdown files and imports them to Neuron Graph."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

from src import neuron_core as neurons

logger = logging.getLogger(__name__)

VAULT_SCAN_GLOBS = ("**/*.md",)
VAULT_SKIP_PARTS = {"node_modules", ".git", ".obsidian"}


def _parse_md(path: Path, max_excerpt: int = 400) -> tuple[str, str, list[str]]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return path.stem, path.stem, []
    title = path.stem
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            fm = parts[1]
            body = parts[2]
            m = re.search(r"(?m)^title:\s*[\"']?(.+?)[\"']?\s*$", fm)
            if m:
                title = m.group(1).strip().strip("\"'")
    lines = []
    for s in body.splitlines():
        s = s.strip()
        if not s or s.startswith("#") or s.startswith("|") or s.startswith("```"):
            continue
        lines.append(s)
        if sum(len(x) for x in lines) > max_excerpt:
            break
    excerpt = " ".join(lines)[:max_excerpt]
    wikilinks = re.findall(r"\[\[([^\]|#]+?)(?:[|#][^\]]*)?\]\]", body)
    wikilinks = [w.strip().replace("\\", "/") for w in wikilinks if w.strip()]
    return title, f"{title} {excerpt} {' '.join(wikilinks)}", wikilinks


def sync_vault_notes(vault_path: Path | str, *, link_wikilinks: bool = True) -> dict[str, Any]:
    vault = Path(vault_path)
    if not vault or not vault.is_dir():
        return {"ok": False, "message": f"vault missing: {vault}", "upserted": 0}
    vault = vault.resolve()

    md_files: list[Path] = []
    for pat in VAULT_SCAN_GLOBS:
        for f in vault.glob(pat):
            r = f.resolve()
            if not r.is_file() or r.suffix.lower() != ".md":
                continue
            try:
                rel = r.relative_to(vault)
                if set(rel.parts) & VAULT_SKIP_PARTS:
                    continue
            except ValueError:
                continue
            if r.name.startswith("."):
                continue
            md_files.append(r)

    md_files = list(dict.fromkeys(md_files))

    ref_to_nid: dict[str, str] = {}
    title_to_nid: dict[str, str] = {}
    pending_links: list[tuple[str, list[str]]] = []
    upserted = 0

    for p in sorted(md_files, key=lambda x: str(x).lower()):
        rel = str(p.relative_to(vault)).replace("\\", "/")
        title, text, links = _parse_md(p)
        base = 0.75 if p.name in ("AGENTS.md", "SCHEMA.md") or "prd" in p.name.lower() else 0.6

        r = neurons.add_node(
            type="vault_note",
            label=(title or p.stem)[:80],
            ref=rel,
            base_weight=base,
            text=text or title or rel,
        )
        nid = r.get("node", {}).get("id")
        if not nid:
            continue
        upserted += 1
        ref_to_nid[rel] = nid
        ref_to_nid[p.stem] = nid
        title_to_nid[title.lower()] = nid
        title_to_nid[p.stem.lower()] = nid
        if link_wikilinks and links:
            pending_links.append((nid, links))

    linked = 0
    if link_wikilinks and pending_links:
        for src_nid, links in pending_links:
            targets = set()
            for link in links:
                tid = ref_to_nid.get(link) or ref_to_nid.get(f"{link}.md") or title_to_nid.get(link.lower())
                if not tid:
                    base = Path(link).stem.lower()
                    tid = title_to_nid.get(base)
                if tid and tid != src_nid:
                    targets.add(tid)
            if targets:
                for tid in list(targets)[:12]:
                    s = neurons.strengthen([src_nid, tid])
                    if s.get("ok"):
                        linked += s.get("updated_edges", 0)

    st = neurons.status().get("stats", {})
    return {
        "ok": True,
        "vault": str(vault),
        "files_scanned": len(md_files),
        "upserted": upserted,
        "wikilink_edges": linked,
        "stats": st,
    }
