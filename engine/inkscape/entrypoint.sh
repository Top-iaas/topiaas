#!/usr/bin/sh 
echo password1 | vncpasswd -f > ~/.vnc/passwd
chmod 0600 ~/.vnc/passwd 
/opt/TurboVNC/bin/vncserver && websockify -D --web=/usr/share/novnc/ --cert=~/novnc.pem 80 localhost:5901 
tail -f /dev/null