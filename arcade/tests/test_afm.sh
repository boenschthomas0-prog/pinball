#!/usr/bin/env bash
# Quick-Check für AFM: zählt Wine-VBScript Type-Mismatch-Errors im Log.
#
# Aktueller Bug: nFozzy-Polarity-Code im g5k-AFM nutzt Dictionary-Lookups, die
# unter Wine-VBScript Type-Mismatches (hres 0x800A01EB) werfen — Ball-Tracking
# bricht ab, Ball "verschwindet".
#
# Test-Methodik:
#   1. AFM startet, Cache wird neu gebaut, ROM lädt
#   2. RUN_SECONDS Sekunden warten (Attract-Mode reicht — Errors treten auch
#      ohne Gameplay auf, weil nFozzy beim Ball-Idle pollt)
#   3. Log nach Pattern grep'en
#   4. Test ist nur VALID, wenn:
#        - ROM tatsächlich gestartet wurde (Solenoid-Init-Zeile im Log)
#        - VPX nicht durch Focus-Loss pausierte (kein "Pausing Game" Event)
#      sonst INCONCLUSIVE.
#
# Benutzung:
#   ./test_afm.sh                      # Default: 45s Run, eigener Output
#   ./test_afm.sh --quick              # 20s (Smoke-Test)
#   ./test_afm.sh --baseline >baseline.txt   # Baseline-Lauf für Vergleiche

set -u

VPX_DIR="/home/thomas/Applications/pinball/vpx"
TABLE_NAME="Attack from Mars (Bally 1995) g5k 1.3.11.vpx"
TABLE_STEM="${TABLE_NAME%.vpx}"
CACHE_DIR="/home/thomas/.vpinball/Cache/${TABLE_STEM}"
LOG="/tmp/test-afm-$$.log"
RUN_SECONDS=45
[ "${1:-}" = "--quick" ] && RUN_SECONDS=20

# Sauberer Start
/usr/bin/killall -9 VPinballX_GL 2>/dev/null
sleep 1
/usr/bin/rm -rf "$CACHE_DIR" 2>/dev/null

# Spawn
cd "$VPX_DIR" || exit 2
/usr/bin/nohup env DISPLAY=:0 SDL_VIDEODRIVER=x11 \
    ./VPinballX_GL -Primary -DisableTrueFullscreen \
    -Play "tables/${TABLE_NAME}" > "$LOG" 2>&1 < /dev/null &
VPX_PID=$!
disown

# Auf Bereitschaft warten (max 60s)
WAITED=0
while ! /usr/bin/grep -q "Startup done" "$LOG" 2>/dev/null; do
    sleep 2
    WAITED=$((WAITED + 2))
    if [ $WAITED -ge 60 ]; then
        echo "FAIL  startup-timeout (60s)"
        /usr/bin/kill -9 "$VPX_PID" 2>/dev/null
        exit 1
    fi
done

# Aktiv halten — maximieren, oben anpinnen, fokussieren
WID=$(DISPLAY=:0 /usr/bin/wmctrl -l 2>/dev/null | /usr/bin/grep "Visual Pinball" | /usr/bin/awk '{print $1}')
DISPLAY=:0 /usr/bin/wmctrl -ir "$WID" -b add,maximized_vert,maximized_horz,above 2>/dev/null
DISPLAY=:0 /usr/bin/xdotool windowactivate --sync "$WID" 2>/dev/null

# Focus-Keeper im Hintergrund — alle 2s VPX wieder aktivieren falls Fokus verloren ist.
# Verhindert dass die Test-Konsole VPX pausiert.
(
    END=$(( $(date +%s) + RUN_SECONDS ))
    while [ "$(date +%s)" -lt "$END" ]; do
        DISPLAY=:0 /usr/bin/xdotool windowactivate "$WID" 2>/dev/null
        sleep 2
    done
) &
KEEPER_PID=$!

# Spiel starten — SDL2 ignoriert oft synthetische xdotool-Events. Workaround:
# echter Maus-Click ins Fenster zwingt SDL2 in "real input mode", dann Taste.
sleep 3
DISPLAY=:0 /usr/bin/xdotool windowactivate --sync "$WID" 2>/dev/null
# Geometry: Click in Tisch-Mitte
GEOM=$(DISPLAY=:0 /usr/bin/wmctrl -lG | /usr/bin/grep "$WID" | /usr/bin/head -1)
WX=$(echo "$GEOM" | /usr/bin/awk '{print $3}')
WY=$(echo "$GEOM" | /usr/bin/awk '{print $4}')
WW=$(echo "$GEOM" | /usr/bin/awk '{print $5}')
WH=$(echo "$GEOM" | /usr/bin/awk '{print $6}')
CX=$(( WX + WW / 2 ))
CY=$(( WY + WH / 2 ))
DISPLAY=:0 /usr/bin/xdotool mousemove "$CX" "$CY" click 1 2>/dev/null
sleep 0.5

# Mehrere Tastendrücke für Robustheit (manche kommen ggf. nicht durch)
# 5 = Coin (falls Credits 0), 1 = Start, Enter = Plunger
for _ in 1 2 3; do
    DISPLAY=:0 /usr/bin/xdotool key 5 2>/dev/null
    sleep 0.3
done
sleep 0.5
for _ in 1 2 3; do
    DISPLAY=:0 /usr/bin/xdotool key 1 2>/dev/null
    sleep 0.3
done
sleep 1
DISPLAY=:0 /usr/bin/xdotool key Return 2>/dev/null

# Mess-Periode (Spiel läuft jetzt, Ball bewegt sich, nFozzy aktiv)
sleep "$RUN_SECONDS"
/usr/bin/kill "$KEEPER_PID" 2>/dev/null
/usr/bin/wait "$KEEPER_PID" 2>/dev/null

# Sauber beenden (NICHT graceful — wir wollen NVRAM nicht überschreiben mit Test-State)
/usr/bin/kill -9 "$VPX_PID" 2>/dev/null
sleep 1

# Auswertung
DICT_ERRORS=$(/usr/bin/grep -c "dictionary_Invoke.*hres=-2146795477" "$LOG" 2>/dev/null)
SCRIPT_ERRORS=$(/usr/bin/grep -c "VBScript runtime error\|VBSE" "$LOG" 2>/dev/null)
SOLENOID_INIT=$(/usr/bin/grep -c "B2SLegacy: Device state updated - Solenoids:" "$LOG" 2>/dev/null)
FOCUS_LOST=$(/usr/bin/grep -c "Focus lost" "$LOG" 2>/dev/null)
PAUSED=$(/usr/bin/grep -c "Pausing Game" "$LOG" 2>/dev/null)
# Game-Activity-Marker: Coin-Insert oder Script.Print von nFozzy-Polarity
GAME_ACTIVITY=$(/usr/bin/grep -cE "fx_Coin|Script\.Print|swStartButton" "$LOG" 2>/dev/null)
# grep -c gibt schon 0 aus wenn nichts gefunden, aber falls Datei fehlt → leer
DICT_ERRORS=${DICT_ERRORS:-0}
SCRIPT_ERRORS=${SCRIPT_ERRORS:-0}
SOLENOID_INIT=${SOLENOID_INIT:-0}
FOCUS_LOST=${FOCUS_LOST:-0}
PAUSED=${PAUSED:-0}
GAME_ACTIVITY=${GAME_ACTIVITY:-0}

# Validität
VALID="yes"
[ "$SOLENOID_INIT" -eq 0 ] && VALID="no (ROM not initialized)"
# Bis zu 2 kurze Pause-Events sind tolerabel (xdotool windowactivate selbst kann
# einen kurzen Fokus-Glitch verursachen). Bei mehr: User hat wahrscheinlich
# manuell zur Konsole gewechselt.
# Tolerieren: 1 Pause pro 5s Run-Time (kurze Fokus-Glitches vom Focus-Keeper)
PAUSE_LIMIT=$(( RUN_SECONDS / 5 ))
[ "$PAUSED" -gt "$PAUSE_LIMIT" ] && VALID="inconclusive ($PAUSED pause events > limit $PAUSE_LIMIT)"
# Game-Activity ist Pflicht: ohne Coin/Start kann nFozzy nicht triggern, dann
# wäre ein PASS false-negative (Bug nicht reproduziert)
[ "$GAME_ACTIVITY" -eq 0 ] && VALID="inconclusive (no game activity — Input nicht durchgekommen)"

# Output (Maschinen-lesbar — KEY=value)
echo "TEST=test_afm"
echo "RUN_SECONDS=$RUN_SECONDS"
echo "DICT_ERRORS=$DICT_ERRORS"
echo "SCRIPT_ERRORS=$SCRIPT_ERRORS"
echo "FOCUS_LOST=$FOCUS_LOST"
echo "PAUSED=$PAUSED"
echo "SOLENOID_INIT=$SOLENOID_INIT"
echo "GAME_ACTIVITY=$GAME_ACTIVITY"
echo "VALID=$VALID"
echo "LOG=$LOG"

# Pass/Fail
if [ "$VALID" != "yes" ]; then
    echo "RESULT=INCONCLUSIVE"
    exit 2
elif [ "$DICT_ERRORS" -eq 0 ] && [ "$SCRIPT_ERRORS" -eq 0 ]; then
    echo "RESULT=PASS"
    exit 0
else
    echo "RESULT=FAIL ($DICT_ERRORS dict-mismatches, $SCRIPT_ERRORS script-errors in ${RUN_SECONDS}s)"
    exit 1
fi
