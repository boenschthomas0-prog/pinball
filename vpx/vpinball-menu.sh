#!/bin/bash
#
# VPinball Menu Launcher - robust für Wayland/XWayland
#
# Key learnings (2026-05-20):
# - User läuft Ubuntu GNOME mit Wayland (XDG_SESSION_TYPE=wayland)
# - VPinball ist X11/SDL3, läuft via XWayland
# - Bildschirm-Rotation per xrandr funktioniert nicht (GPU BadMatch) -> ignorieren
# - VPX-Cache wird manchmal korrupt -> beim Start prüfen
# - SDL_VIDEODRIVER=x11 explizit forcieren (sonst kann SDL fallback auf wayland-native versuchen)

set -u

# X11/Display-Umgebung erzwingen (auch bei Start aus dem Desktop-Launcher)
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/home/thomas/.Xauthority}"
export SDL_VIDEODRIVER=x11
export GDK_BACKEND=x11

VPX_DIR="/home/thomas/Applications/pinball/vpx"
TABLES_DIR="$VPX_DIR/tables"
LOG_FILE="$VPX_DIR/last-run.log"
STATUS_FILE="$VPX_DIR/table-status.txt"
LOCK_FILE="/tmp/vpinball-menu.lock"
CACHE_DIR="/home/thomas/.vpinball/Cache"

cd "$VPX_DIR" || exit 1

# --- Single-Instance über flock ---------------------------------------------
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
    zenity --error --width=420 \
        --text="Das VPinball-Menü läuft bereits.\n(Lock: $LOCK_FILE)" 2>/dev/null
    exit 1
fi

# --- Aufräumen vor jedem Start ----------------------------------------------
# Tote VPinball-Prozesse killen (geistert manchmal rum nach Abstürzen)
pkill -9 -f VPinballX_GL 2>/dev/null
sleep 1

# --- Tisch-Status -----------------------------------------------------------
declare -A STATUS=(
    ["alien13.vpx"]="OK    - Alien (bestätigt)"
    ["BTILC_2026_Original_1.0.0.vpx"]="OK    - Big Trouble in Little China"
    ["Futurama (Original 2024) v1.2.2.vpx"]="?     - Futurama (Original)"
    ["GOTG_2.1.0.vpx"]="?     - Guardians of the Galaxy"
    ["Ramones (HauntFreaks 2021) v2.0.vpx"]="?     - Ramones"
    ["F-14 Tomcat (Williams 1987) 1.6.vpx"]="?     - F-14 Tomcat (PinMAME-Fix angewendet)"
    ["Bram Stokers Dracula (Williams 1993) VPW 1.0.1.vpx"]="KAPUTT - Dracula (PinMAME ROMs fehlen)"
    ["Halloween (Granit 2020).vpx"]="NEU   - Halloween (Granit)"
    ["Stranger Things (Granit 2020).vpx"]="NEU   - Stranger Things (Granit)"
    ["Houdini (Granit 2020).vpx"]="NEU   - Houdini (Granit)"
    ["Alice Cooper Nightmare Castle (Ling Woo).vpx"]="NEU   - Alice Cooper Nightmare Castle"
    ["Yellow Submarine (Giantomasi 2020).vpx"]="NEU   - Yellow Submarine"
    ["JP's VPX7 Rev3 Elasticity_Test.vpx"]="TEST  - Elasticity Test"
    ["Nudge Test and Calibration.vpx"]="TEST  - Nudge Test"
    ["Screen Size Calibration.vpx"]="TEST  - Screen Calibration"
)

if [ -f "$STATUS_FILE" ]; then
    while IFS='|' read -r fname stat; do
        [ -n "$fname" ] && STATUS["$fname"]="$stat"
    done < "$STATUS_FILE"
fi

# --- Haupt-Loop: Menü -> Spiel -> Menü -> ... bis User Schluss macht --------
while true; do
    # Tisch-Liste aufbauen
    ARGS=()
    while IFS= read -r -d '' file; do
        name="$(basename "$file")"
        label="${STATUS[$name]:-?  - $name}"
        ARGS+=("$name" "$label")
    done < <(find "$TABLES_DIR" -maxdepth 1 -name '*.vpx' -print0 | sort -z)

    if [ ${#ARGS[@]} -eq 0 ]; then
        zenity --error --text="Keine Tables in $TABLES_DIR gefunden." 2>/dev/null
        break
    fi

    CHOICE="$(zenity --list \
        --title="VPinball - welchen Tisch?" \
        --text="Wähle einen Tisch.\nESC im Spiel beendet den Tisch (du landest wieder hier)." \
        --width=780 --height=600 \
        --column="Datei" --column="Status / Beschreibung" \
        --hide-column=1 --print-column=1 \
        "${ARGS[@]}" 2>/dev/null)"

    # Abbruch (Schließen oder Cancel) -> Menü beenden
    [ -z "${CHOICE:-}" ] && break

    # --- Pre-Launch Aufräumarbeiten -----------------------------------------
    # Tote VPX-Reste vorm Start sicher weg
    pkill -9 -f VPinballX_GL 2>/dev/null
    sleep 0.5

    # Cache des Tisches löschen falls möglicherweise korrupt
    # (Sicherheit > Geschwindigkeit; lädt halt 5 Sek länger neu)
    table_base="${CHOICE%.vpx}"
    if [ -d "$CACHE_DIR/$table_base" ]; then
        rm -rf "$CACHE_DIR/$table_base"
    fi

    echo "==== $(date '+%F %T') - Starting: $CHOICE ====" >> "$LOG_FILE"

    # --- VPinball starten ---------------------------------------------------
    ./VPinballX_GL -Primary -DisableTrueFullscreen -Play "tables/$CHOICE" >> "$LOG_FILE" 2>&1
    RC=$?
    echo "==== $(date '+%F %T') - Exit Code: $RC ====" >> "$LOG_FILE"

    # --- Nach dem Spiel -----------------------------------------------------
    if [ $RC -ne 0 ] && [ $RC -ne 137 ] && [ $RC -ne 143 ]; then
        # Echter Crash (nicht durch SIGTERM/SIGKILL)
        if ! zenity --question --width=520 \
            --text="Tisch '$CHOICE' hat sich mit Code $RC beendet.\n\nLog: $LOG_FILE\n\nWeitermachen mit anderem Tisch?" 2>/dev/null; then
            break
        fi
    fi
    # Sonst: zurück ins Menü ohne Frage
done

exit 0
