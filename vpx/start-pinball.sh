#!/bin/bash

cd /home/thomas/Applications/pinball/vpx || exit

# Bildschirm hochkant drehen
xrandr --output DP-1 --rotate left

# Spiel starten
./VPinballX_GL -Primary -DisableTrueFullscreen -Play "tables/alien13.vpx"

# Nach dem Beenden wieder normal drehen
xrandr --output DP-1 --rotate normal
