#!/usr/bin/env bash
# PreToolUse: deny every tool call once the 5h limit is at or above 75%.
# The status line writes "<percent> <epoch>" to ~/.claude/usage-5h.txt.
# Ignores readings older than 10 minutes. Override: touch ~/.claude/usage-stop-off
f="$HOME/.claude/usage-5h.txt"; limit=75
[ -e "$HOME/.claude/usage-stop-off" ] && exit 0
[ -r "$f" ] || exit 0
read -r pct ts < "$f"
[ -n "$pct" ] && [ -n "$ts" ] || exit 0
[ $(( $(date +%s) - ts )) -le 600 ] || exit 0
if awk -v p="$pct" -v l="$limit" 'BEGIN{exit !(p>=l)}'; then
  jq -n --arg p "$pct" '{hookSpecificOutput:{hookEventName:"PreToolUse",permissionDecision:"deny",
    permissionDecisionReason:("Hard stop: 5h usage is at " + $p + "% (limit 75%). Stop all work now, tell the user what is done and what is left, and do not call more tools.")}}'
fi
