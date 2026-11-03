# rules.sh — managed-block machinery (research R6, FR-006/FR-006a).
# shellcheck shell=bash
# Markers are matched by their literal substrings; exactly one pair per file.
MARK_BEGIN="<!-- genesis-skills:begin"
MARK_END="<!-- genesis-skills:end -->"
MARK_MGMT="<!-- managed by genesis-skills install.sh; edits inside are replaced on refresh -->"

# Generate the full block text (markers included) from the instruction list.
# $1 = agents csv (sorted), $2 = date-version token, stdin = instruction file paths.
block_generate() {
  local agents="$1" ver="$2" f name desc apply
  printf '%s agents=%s v=%s -->\n' "$MARK_BEGIN" "$agents" "$ver"
  printf '%s\n\n' "$MARK_MGMT"
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    name="$(inst_name "$f")"
    desc="$(fm_value "$f" description)"
    apply="$(fm_value "$f" applyTo)"
    printf '## Review guidance: %s\n\n' "$name"
    printf 'Source: .github/instructions/%s.instructions.md' "$name"
    [ -n "$apply" ] && printf ' — apply to: %s' "$apply"
    [ -n "$desc" ] && printf '\n\n%s' "$desc"
    printf '\n\n'
    fm_strip "$f"
    printf '\n'
  done
  printf '%s\n' "$MARK_END"
}

# Does the file currently hold a managed block?
block_present() { [ -f "$1" ] && grep -Fq "$MARK_BEGIN" "$1"; }

# Extract the block's inner body from file (marker lines excluded, so hashes
# stay stable when the agents= attribute or version token in the begin marker
# changes but the managed content does not).
block_extract() { # $1 = file
  awk -v begin="$MARK_BEGIN" -v end="$MARK_END" '
    index($0, begin) && !inb { inb=1; next }
    inb && index($0, end) { exit }
    inb { print }
  ' "$1"
}

# Insert (at end) or replace the managed block in $1. Block text on stdin
# (written to $2 temp by caller for awk). Leaves $1 modified in place.
block_upsert() { # $1 = file (may be missing), $2 = block text file
  local file="$1" block="$2"
  if [ -e "$file" ] && block_present "$file"; then
    awk -v begin="$MARK_BEGIN" -v end="$MARK_END" -v bf="$block" '
      index($0, begin) && !done {
        done=1; skipline=1
        while ((getline line < bf) > 0) print line
        close(bf)
      }
      skipline { if (index($0, end)) skipline=0; next }
      !done && index($0, begin) { next }
      { print }
    ' "$file" > "$file.genesis-tmp.$$" && mv -f "$file.genesis-tmp.$$" "$file"
  elif [ -e "$file" ]; then
    cat "$file" > "$file.genesis-tmp.$$"
    printf '\n' >> "$file.genesis-tmp.$$"
    cat "$block" >> "$file.genesis-tmp.$$"
    mv -f "$file.genesis-tmp.$$" "$file"
  else
    cat "$block" > "$file"
  fi
}

# Remove the managed block (both marker lines inclusive) from $1.
block_remove() { # $1 = file
  [ -f "$1" ] || return 0
  block_present "$1" || return 0
  awk -v begin="$MARK_BEGIN" -v end="$MARK_END" '
    index($0, begin) { skipline=1 }
    skipline { if (index($0, end)) skipline=0; next }
    { print }
  ' "$1" > "$1.genesis-tmp.$$" && mv -f "$1.genesis-tmp.$$" "$1"
}
