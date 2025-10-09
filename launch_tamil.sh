#!/bin/bash
# Tamil Assistant Launcher Script

# Kill any existing Tamil Assistant processes
pkill -f tamil_sidepanel.py

# Start Tamil Assistant
cd /home/radnus/Projects/tamil-assistant
python3 tamil_sidepanel.py &

# Wait for it to start
sleep 2

# Force it to be visible
i3-msg '[title="Tamil Assistant"] floating enable'
i3-msg '[title="Tamil Assistant"] move position 1520 0'
i3-msg '[title="Tamil Assistant"] focus'
i3-msg '[title="Tamil Assistant"] move to workspace current'

# Show a notification
notify-send "Tamil Assistant" "Launched successfully!"
