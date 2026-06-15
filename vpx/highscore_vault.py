#!/usr/bin/env python3
"""
highscore_vault.py — Highscore-Tresor für das VPinball-Arcade-Menü.

Sichert und stellt die Highscores ALLER Tische wieder her — tisch-agnostisch.

VPX hat keinen globalen Highscore-Mechanismus: Jeder Tisch entscheidet im
eigenen VBScript, ob und wohin er speichert.
  * Original-Tische  → SaveValue/LoadValue → [<TableName>]-Sektion in
                       ~/.vpinball/VPReg.ini
  * PinMAME-Tische   → NVRAM-Dateien in ~/.vpinball/pinmame/nvram/<rom>.nv

Der Tresor (~/.vpinball/highscore-vault/) wird vom Menü um jeden Tischstart
gelegt:
  * restore_before_launch(vpx) — VOR dem Start: gespeicherte Sektion/NVRAM des
        Tisches in VPReg.ini bzw. nvram/ zurückschreiben. Danach Schnappschuss
        des Ist-Stands als Vergleichsbasis.
  * capture_after_exit(vpx)    — NACH dem Ende: VPReg.ini/NVRAM gegen den
        Schnappschuss diffen, geänderte Sektionen/Dateien dem Tisch zuordnen
        und im Tresor ablegen.

Der Tresor ist per .vpx-Dateiname indiziert und entdeckt die VPReg-Sektion /
NVRAM-Datei jedes Tisches beim ersten Spielen automatisch (Diff) — keine
Pro-Tisch-Konfiguration nötig. Neue Tische sind dadurch automatisch abgedeckt.
Die aktive Wiederherstellung entkoppelt außerdem Tische, die sich denselben
Sektionsnamen teilen (z.B. mehrere [demo]-Tische).

Standalone-Selbsttest:  python3 highscore_vault.py selftest
Tresor anzeigen:        python3 highscore_vault.py dump
"""
import hashlib
import json
import shutil
import time
from pathlib import Path

# ── Pfade ────────────────────────────────────────────────────────────────────
VPINBALL    = Path.home() / '.vpinball'
VPREG       = VPINBALL / 'VPReg.ini'
NVRAM_DIR   = VPINBALL / 'pinmame' / 'nvram'
VAULT_DIR   = VPINBALL / 'highscore-vault'
VAULT_JSON  = VAULT_DIR / 'vault.json'
VAULT_BAK   = VAULT_DIR / 'vault.json.bak'
VPREG_BAK   = VAULT_DIR / 'VPReg.ini.bak'
NVRAM_BLOBS = VAULT_DIR / 'nvram'
VAULT_LOG   = VAULT_DIR / 'vault.log'

# Schnappschuss zwischen restore_before_launch und capture_after_exit
# (gleicher Prozess — das Menü umschließt den Start synchron).
_session = {}


# ── kleine Helfer ────────────────────────────────────────────────────────────
def _log(msg):
    """Eine datierte Zeile in vault.log anhängen (Fehler werden geschluckt)."""
    try:
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        with open(VAULT_LOG, 'a') as f:
            f.write(f'{time.strftime("%F %T")}  {msg}\n')
    except Exception:
        pass


def _read(path):
    """Datei als Text lesen; fehlt sie / ist sie kaputt → leerer String."""
    try:
        return Path(path).read_text(errors='replace')
    except Exception:
        return ''


def _safe(name):
    """.vpx-Dateiname → als Ordnername brauchbar machen."""
    return name.replace('/', '_')


# ── INI: parsen & sektionsweise schreiben ────────────────────────────────────
def _parse_ini(text):
    """INI-Text → {Sektion: {Schlüssel: Wert}}. Groß-/Kleinschreibung bleibt."""
    sections = {}
    cur = None
    for line in text.splitlines():
        s = line.strip()
        if not s or s[0] in ';#':
            continue
        if s.startswith('[') and s.endswith(']'):
            cur = s[1:-1]
            sections.setdefault(cur, {})
        elif '=' in line and cur is not None:
            k, v = line.split('=', 1)
            sections[cur][k.strip()] = v.strip()
    return sections


def _write_sections(path, sections):
    """
    Ganze [Sektion]en in eine INI-Datei einfügen/ersetzen — alles andere
    bleibt unangetastet (Stil von vpinball-menu.py:write_view_override).
    Atomar via .tmp + replace.
    """
    path = Path(path)
    lines = _read(path).splitlines()
    out, written, skip = [], set(), False
    for line in lines:
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            cur = s[1:-1]
            if cur in sections and cur not in written:
                out.append(f'[{cur}]')
                for k, v in sections[cur].items():
                    out.append(f'{k}={v}')
                written.add(cur)
                skip = True            # alten Sektions-Rumpf überspringen
            else:
                out.append(line)
                skip = False
            continue
        if not skip:
            out.append(line)
    for name, kv in sections.items():   # neue, bisher fehlende Sektionen
        if name not in written:
            out.append(f'[{name}]')
            for k, v in kv.items():
                out.append(f'{k}={v}')
    text = '\n'.join(out)
    if text and not text.endswith('\n'):
        text += '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(text)
    tmp.replace(path)


# ── NVRAM-Schnappschuss ──────────────────────────────────────────────────────
def _nvram_snapshot():
    """{Dateiname: sha1} aller *.nv-Dateien im NVRAM-Ordner."""
    snap = {}
    if NVRAM_DIR.is_dir():
        for p in sorted(NVRAM_DIR.glob('*.nv')):
            try:
                snap[p.name] = hashlib.sha1(p.read_bytes()).hexdigest()
            except Exception:
                pass
    return snap


# ── Tresor laden / speichern ─────────────────────────────────────────────────
def _load_vault():
    """vault.json laden; bei Defekt vault.json.bak versuchen; sonst leer."""
    for p in (VAULT_JSON, VAULT_BAK):
        if p.exists():
            try:
                d = json.loads(p.read_text())
                if isinstance(d, dict):
                    d.setdefault('version', 1)
                    d.setdefault('tables', {})
                    return d
            except Exception as e:
                _log(f'Tresor aus {p.name} unlesbar: {e}')
    return {'version': 1, 'tables': {}}


def _save_vault(vault):
    """vault.json atomar schreiben; vorher vault.json + VPReg.ini sichern."""
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    if VAULT_JSON.exists():
        shutil.copy2(VAULT_JSON, VAULT_BAK)
    if VPREG.exists():
        try:
            shutil.copy2(VPREG, VPREG_BAK)
        except Exception:
            pass
    tmp = VAULT_JSON.with_name('vault.json.tmp')
    tmp.write_text(json.dumps(vault, indent=2, ensure_ascii=False) + '\n')
    tmp.replace(VAULT_JSON)


# ── öffentliche API ──────────────────────────────────────────────────────────
def restore_before_launch(vpx):
    """
    VOR dem Tischstart aufrufen (nach pkill, vor Popen). Stellt die im Tresor
    gespeicherte VPReg-Sektion und die NVRAM-Dateien des Tisches wieder her
    und legt anschließend den Vergleichs-Schnappschuss an.
    """
    global _session
    try:
        vault = _load_vault()
        entry = vault.get('tables', {}).get(vpx)
        if entry:
            secs = entry.get('vpreg') or {}
            if secs:
                _write_sections(VPREG, secs)
                _log(f'{vpx}: Sektion(en) {list(secs)} in VPReg.ini wiederhergestellt')
            for nv in entry.get('nvram') or []:
                src = NVRAM_BLOBS / _safe(vpx) / nv
                if src.is_file():
                    NVRAM_DIR.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, NVRAM_DIR / nv)
                    _log(f'{vpx}: NVRAM {nv} wiederhergestellt')
    except Exception as e:
        _log(f'{vpx}: restore fehlgeschlagen: {e}')
    # Schnappschuss IMMER nehmen (auch wenn das Restore oben scheiterte) —
    # er ist die Vergleichsbasis für capture_after_exit.
    try:
        _session = {
            'vpx': vpx,
            'vpreg': _parse_ini(_read(VPREG)),
            'nvram': _nvram_snapshot(),
        }
    except Exception as e:
        _session = {'vpx': vpx, 'vpreg': {}, 'nvram': {}}
        _log(f'{vpx}: Schnappschuss fehlgeschlagen: {e}')


def capture_after_exit(vpx):
    """
    NACH dem Tischende aufrufen (bei JEDEM Exit-Code — gerade ein Crash macht
    das Sichern wichtig). Difft VPReg.ini/NVRAM gegen den Schnappschuss und
    legt geänderte Sektionen/Dateien unter diesem .vpx-Dateinamen im Tresor ab.
    """
    try:
        if not _session or _session.get('vpx') != vpx:
            _log(f'{vpx}: kein passender Schnappschuss — capture übersprungen')
            return

        before_vp = _session.get('vpreg', {})
        after_vp = _parse_ini(_read(VPREG))
        # neue ODER geänderte Sektionen; leere Sektionen ignorieren (Schutz vor
        # einer durch den Shutdown-Crash abgeschnittenen VPReg.ini).
        changed_vp = {s: kv for s, kv in after_vp.items()
                      if kv and before_vp.get(s) != kv}

        before_nv = _session.get('nvram', {})
        after_nv = _nvram_snapshot()
        changed_nv = [n for n, sig in after_nv.items()
                      if before_nv.get(n) != sig]

        if not changed_vp and not changed_nv:
            return  # nichts gespielt-gespeichert — Tresor bleibt unangetastet

        vault = _load_vault()
        entry = vault['tables'].setdefault(vpx, {})
        vp_have = entry.setdefault('vpreg', {})

        for sec, kv in changed_vp.items():
            old = vp_have.get(sec)
            # Schrumpf-Schutz: hatte der Tresor diese Sektion schon mit MEHR
            # Schlüsseln, ist der neue Stand vermutlich beschädigt → alt behalten.
            if old and len(kv) < len(old):
                _log(f'{vpx}: [{sec}] {len(old)}→{len(kv)} Schlüssel — '
                     f'verdächtig, alter Stand behalten')
                continue
            vp_have[sec] = kv

        if changed_nv:
            dest = NVRAM_BLOBS / _safe(vpx)
            dest.mkdir(parents=True, exist_ok=True)
            have = set(entry.get('nvram') or [])
            for n in changed_nv:
                try:
                    shutil.copy2(NVRAM_DIR / n, dest / n)
                    have.add(n)
                except Exception as e:
                    _log(f'{vpx}: NVRAM {n} sichern fehlgeschlagen: {e}')
            entry['nvram'] = sorted(have)

        entry['updated'] = time.strftime('%F %T')
        _save_vault(vault)
        _log(f'{vpx}: gesichert — VPReg {list(changed_vp) or "—"}, '
             f'NVRAM {changed_nv or "—"}')
    except Exception as e:
        _log(f'{vpx}: capture fehlgeschlagen: {e}')


# ── Selbsttest / CLI ─────────────────────────────────────────────────────────
def _selftest():
    """Isolierter Round-Trip-Test in einem temporären Ordner."""
    import tempfile
    global VPINBALL, VPREG, NVRAM_DIR, VAULT_DIR, VAULT_JSON, VAULT_BAK
    global VPREG_BAK, NVRAM_BLOBS, VAULT_LOG, _session

    tmp = Path(tempfile.mkdtemp(prefix='hsvault-test-'))
    VPINBALL    = tmp
    VPREG       = tmp / 'VPReg.ini'
    NVRAM_DIR   = tmp / 'pinmame' / 'nvram'
    VAULT_DIR   = tmp / 'highscore-vault'
    VAULT_JSON  = VAULT_DIR / 'vault.json'
    VAULT_BAK   = VAULT_DIR / 'vault.json.bak'
    VPREG_BAK   = VAULT_DIR / 'VPReg.ini.bak'
    NVRAM_BLOBS = VAULT_DIR / 'nvram'
    VAULT_LOG   = VAULT_DIR / 'vault.log'

    ok = True

    def check(label, cond):
        nonlocal ok
        ok = ok and cond
        print(f'  [{"PASS" if cond else "FAIL"}]  {label}')

    # 1) Round-Trip: erster Lauf entdeckt + sichert die Sektion
    VPREG.write_text('[gotg_2020]\nHighScore1=75000000\nHighScore1Name=MPT\n'
                     'Credits=6\n[other]\nKeep=yes\n')
    restore_before_launch('GOTG.vpx')                       # noch kein Eintrag
    # „Spiel" verbessert den Highscore:
    _write_sections(VPREG, {'gotg_2020': {'HighScore1': '99000000',
                                          'HighScore1Name': 'ABC',
                                          'Credits': '6'}})
    capture_after_exit('GOTG.vpx')
    v = _load_vault()
    check('Sektion gotg_2020 unter GOTG.vpx gesichert',
          v['tables'].get('GOTG.vpx', {}).get('vpreg', {})
           .get('gotg_2020', {}).get('HighScore1') == '99000000')
    check('fremde Sektion [other] NICHT gesichert',
          'other' not in v['tables'].get('GOTG.vpx', {}).get('vpreg', {}))

    # 2) Aktive Wiederherstellung: Sektion aus VPReg.ini löschen → restore holt sie zurück
    _write_sections(VPREG, {'other': {'Keep': 'yes'}})       # ersetzt other, lässt gotg…
    VPREG.write_text('[other]\nKeep=yes\n')                  # gotg_2020 ganz weg
    restore_before_launch('GOTG.vpx')
    after = _parse_ini(_read(VPREG))
    check('gotg_2020 nach Restore wieder in VPReg.ini',
          after.get('gotg_2020', {}).get('HighScore1') == '99000000')

    # 3) Crash-Schutz: abgeschnittene/leere Sektion darf den Tresor NICHT überschreiben
    VPREG.write_text('[gotg_2020]\n[other]\nKeep=yes\n')     # gotg_2020 leer
    restore_before_launch('GOTG.vpx')   # stellt 99000000 wieder her + Schnappschuss
    VPREG.write_text('[gotg_2020]\n[other]\nKeep=yes\n')     # „Crash": Sektion leer
    capture_after_exit('GOTG.vpx')
    v = _load_vault()
    check('leere Sektion überschreibt guten Tresor-Stand nicht',
          v['tables']['GOTG.vpx']['vpreg']['gotg_2020']['HighScore1'] == '99000000')

    # 4) Kollision: zwei Tische teilen sich [demo] — je eigener Tresor-Slot
    VPREG.write_text('[demo]\nHighScore1=100\nHighScore1Name=AAA\n')
    restore_before_launch('TableA.vpx')
    _write_sections(VPREG, {'demo': {'HighScore1': '111', 'HighScore1Name': 'AAA'}})
    capture_after_exit('TableA.vpx')
    restore_before_launch('TableB.vpx')
    _write_sections(VPREG, {'demo': {'HighScore1': '222', 'HighScore1Name': 'BBB'}})
    capture_after_exit('TableB.vpx')
    restore_before_launch('TableA.vpx')          # A wieder laden
    a = _parse_ini(_read(VPREG))
    check('Kollision entkoppelt: A behält 111 trotz B',
          a.get('demo', {}).get('HighScore1') == '111')

    # 5) NVRAM-Round-Trip
    NVRAM_DIR.mkdir(parents=True, exist_ok=True)
    (NVRAM_DIR / 'gotg.nv').write_bytes(b'\x01\x02SCORE')
    restore_before_launch('GOTG.vpx')
    (NVRAM_DIR / 'gotg.nv').write_bytes(b'\x09\x09NEWSCORE')   # „Spiel"
    capture_after_exit('GOTG.vpx')
    (NVRAM_DIR / 'gotg.nv').unlink()                            # NVRAM verloren
    restore_before_launch('GOTG.vpx')
    check('NVRAM gotg.nv wiederhergestellt',
          (NVRAM_DIR / 'gotg.nv').read_bytes() == b'\x09\x09NEWSCORE')

    print(f'\n  Testordner: {tmp}')
    print('  ' + ('ALLE TESTS BESTANDEN' if ok else '*** TESTS FEHLGESCHLAGEN ***'))
    shutil.rmtree(tmp, ignore_errors=True)
    return ok


def _dump():
    """Den echten Tresor menschenlesbar ausgeben."""
    v = _load_vault()
    print(f'Tresor: {VAULT_JSON}')
    tables = v.get('tables', {})
    if not tables:
        print('  (leer — noch kein Tisch gesichert)')
        return
    for fn, e in sorted(tables.items()):
        secs = ', '.join(e.get('vpreg', {})) or '—'
        nv = ', '.join(e.get('nvram', [])) or '—'
        print(f'  {fn}')
        print(f'      VPReg-Sektion(en): {secs}')
        print(f'      NVRAM:             {nv}')
        print(f'      zuletzt:           {e.get("updated", "?")}')


if __name__ == '__main__':
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'selftest'
    if cmd == 'dump':
        _dump()
    elif cmd == 'selftest':
        sys.exit(0 if _selftest() else 1)
    else:
        print(__doc__)
        sys.exit(2)
