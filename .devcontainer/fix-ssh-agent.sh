#!/bin/bash
# Find the SSH agent socket that actually has keys
for socket in /tmp/auth-agent*/listener.sock; do
    if [ -S "$socket" ]; then
        if SSH_AUTH_SOCK="$socket" ssh-add -l >/dev/null 2>&1; then
            export SSH_AUTH_SOCK="$socket"
            echo "export SSH_AUTH_SOCK=\"$socket\"" >> /home/vscode/.bashrc
            break
        fi
    fi
done
