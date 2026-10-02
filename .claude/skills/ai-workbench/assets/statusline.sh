#!/usr/bin/env bash
# ~/.claude/statusline.sh
#
# AI WORKBENCH status line for Claude Code.
# Mirrors the palette used in ~/.config/starship.toml:
#   soft_green   #00ff9f  -> directory, 5h-limit bar (healthy)
#   cyber_purple #9d4bff  -> git branch
#   neon_cyan    #00fff9  -> model, context bar (healthy)
#   warn_amber   #ffb000  -> either bar, 70-89% used
#   error_red    #ff003c  -> either bar, >=90% used (danger)
#   muted_grey   #5c5c6e  -> separators / low-emphasis text
#
# Renders: dir on Ψ branch │ model │ ctx ▓▓▓▓▓░░░░░ 48% │ 5h ▓▓░░░░░░░░ 20% │ 7d ▓░░░░░░░░░ 13% │ in 12.3M 97% cached  out 85k
#
# The 5h segment (Claude.ai subscription rate-limit usage) only appears when
# `.rate_limits.five_hour` is present in the payload — it's omitted entirely
# for accounts/sessions where Claude Code doesn't report it, rather than
# showing a broken or zeroed-out bar.
#
# Session token totals need node and ~/.claude/statusline-tokens.mjs; without
# them that segment is skipped.
#
# Reads the statusLine JSON payload from stdin (see Claude Code docs).

input=$(cat)

# ---- 24-bit ANSI truecolor palette -----------------------------------------
C_RESET=$'\033[0m'
C_GREEN=$'\033[38;2;0;255;159m'    # soft_green
C_PURPLE=$'\033[38;2;157;75;255m'  # cyber_purple
C_CYAN=$'\033[38;2;0;255;249m'     # neon_cyan
C_AMBER=$'\033[38;2;255;176;0m'    # warn_amber
C_RED=$'\033[38;2;255;0;60m'       # error_red
C_GREY=$'\033[38;2;92;92;110m'     # muted_grey

sep="${C_GREY} │ ${C_RESET}"

# ---- directory: shorten $HOME to ~, truncate to last 3 path segments ------
dir_raw=$(printf '%s' "$input" | jq -r '.workspace.current_dir // .cwd // "."')
dir_disp=${dir_raw/#$HOME/\~}

IFS='/' read -ra parts <<< "$dir_disp"
n=${#parts[@]}
if (( n > 3 )); then
    short_dir="…/${parts[n-3]}/${parts[n-2]}/${parts[n-1]}"
else
    short_dir="$dir_disp"
fi
[ -z "$short_dir" ] && short_dir="/"

# ---- git branch (skip optional locks so we never block/interfere) ---------
branch=""
if git -C "$dir_raw" --no-optional-locks rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    branch=$(git -C "$dir_raw" --no-optional-locks branch --show-current 2>/dev/null)
fi

# ---- model ------------------------------------------------------------------
model=$(printf '%s' "$input" | jq -r '.model.display_name // .model.id // "Claude"')

# ---- context window usage ----------------------------------------------------
# used_percentage is pre-calculated by Claude Code (0-100), based on
# total_input_tokens vs context_window_size. Preferred over deriving it
# ourselves from raw token counts.
used_pct=$(printf '%s' "$input" | jq -r '.context_window.used_percentage // empty')

# ---- 5-hour rate limit (Claude.ai subscription usage) ------------------------
# Only present for subscribers, and only after the first API response of the
# session while the window is still active. Must degrade gracefully when
# entirely absent (jq's `// empty` already collapses null-propagation from a
# missing `.rate_limits` object down to an empty string).
five_pct=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
week_pct=$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')

# Feed the optional usage hard-stop hook (~/.claude/hooks/usage-stop.sh), which
# reads "<percent> <epoch>" from this file. Written only when the hook is installed.
if [ -n "$five_pct" ] && [ -f "$HOME/.claude/hooks/usage-stop.sh" ]; then
    printf '%s %s\n' "$five_pct" "$(date +%s)" > "$HOME/.claude/usage-5h.txt"
fi

# ---- session tokens (summed from the transcript; see statusline-tokens.mjs) ---
transcript=$(printf '%s' "$input" | jq -r '.transcript_path // empty')
tokens=""
[ -n "$transcript" ] && tokens=$(node "$HOME/.claude/statusline-tokens.mjs" "$transcript" 2>/dev/null)

# ---- bar widget helpers -------------------------------------------------------
BAR_WIDTH=10
BLOCK_FULL="▓"
BLOCK_EMPTY="░"

# make_bar <pct 0-100> -> prints a BAR_WIDTH-wide block meter
make_bar() {
    local pct=$1 filled empty i bar=""
    filled=$(( (pct * BAR_WIDTH + 50) / 100 ))
    (( filled < 0 )) && filled=0
    (( filled > BAR_WIDTH )) && filled=$BAR_WIDTH
    empty=$(( BAR_WIDTH - filled ))
    for (( i = 0; i < filled; i++ )); do bar+="$BLOCK_FULL"; done
    for (( i = 0; i < empty; i++ )); do bar+="$BLOCK_EMPTY"; done
    printf '%s' "$bar"
}

# bar_color <pct> <healthy_color> -> healthy below 70%, amber 70-89%, red >=90%
bar_color() {
    local pct=$1 healthy=$2
    if (( pct >= 90 )); then
        printf '%s' "$C_RED"
    elif (( pct >= 70 )); then
        printf '%s' "$C_AMBER"
    else
        printf '%s' "$healthy"
    fi
}

# clamp_pct <raw float/int pct> -> integer, clamped to [0,100]
clamp_pct() {
    local raw="$1" n
    n=$(printf '%.0f' "$raw" 2>/dev/null)
    [ -z "$n" ] && n=0
    (( n < 0 )) && n=0
    (( n > 100 )) && n=100
    printf '%s' "$n"
}

# ---- assemble ---------------------------------------------------------------
out="${C_GREEN}${short_dir}${C_RESET}"

if [ -n "$branch" ]; then
    out="${out}${C_GREY} on ${C_PURPLE}Ψ ${branch}${C_RESET}"
fi

out="${out}${sep}${C_CYAN}${model}${C_RESET}"

if [ -n "$used_pct" ] && [ "$used_pct" != "null" ]; then
    pct_int=$(clamp_pct "$used_pct")
    bar=$(make_bar "$pct_int")
    ctx_color=$(bar_color "$pct_int" "$C_CYAN")
    out="${out}${sep}${ctx_color}ctx ${bar} ${pct_int}%${C_RESET}"
fi

if [ -n "$five_pct" ] && [ "$five_pct" != "null" ]; then
    pct_int=$(clamp_pct "$five_pct")
    bar=$(make_bar "$pct_int")
    five_color=$(bar_color "$pct_int" "$C_GREEN")
    five_reset=$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
    reset_txt=""
    [ -n "$five_reset" ] && reset_txt=" resets $(date -d "@${five_reset%.*}" +%H:%M 2>/dev/null)"
    out="${out}${sep}${five_color}5h ${bar} ${pct_int}%${reset_txt}${C_RESET}"
fi

if [ -n "$week_pct" ] && [ "$week_pct" != "null" ]; then
    pct_int=$(clamp_pct "$week_pct")
    bar=$(make_bar "$pct_int")
    week_color=$(bar_color "$pct_int" "$C_GREEN")
    out="${out}${sep}${week_color}7d ${bar} ${pct_int}%${C_RESET}"
fi

if [ -n "$tokens" ]; then
    out="${out}${sep}${C_GREY}${tokens}${C_RESET}"
fi

printf '%s\n' "$out"
