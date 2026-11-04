# rules.sh — managed-block machinery (research R6, FR-006/FR-006a).
# shellcheck shell=bash
# Markers are matched by their literal substrings; exactly one pair per file.
# Current generation of markers (what this installer writes).
MARK_BEGIN="<!-- omd-skills:begin"
MARK_END="<!-- omd-skills:end -->"
MARK_MGMT="<!-- managed by omd-skills install.sh; edits inside are replaced on refresh -->"
# Legacy generation (recognize-only: a pre-rename install is still refreshed,
# migrated and uninstalled, but these markers are never written).
LEGACY_MARK_BEGIN="<!-- genesis-skills:begin"
LEGACY_MARK_END="<!-- genesis-skills:end -->"

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

# Does the file currently hold a managed block (either marker generation)?
# A legacy-only file must still be found, so it is migrated rather orphaned.
block_present() {
  [ -f "$1" ] || return 1
  grep -Fq "$MARK_BEGIN" "$1" || grep -Fq "$LEGACY_MARK_BEGIN" "$1"
}

# Was the block in $1 written by the legacy (pre-rename) installer?
block_is_legacy() { # $1 = file
  [ -f "$1" ] && grep -Fq "$LEGACY_MARK_BEGIN" "$1"
}

# Extract the block's inner body from file (marker lines excluded, so hashes
# stay stable when the agents= attribute or version token in the begin marker
# changes, when a legacy block is migrated, or when the managed content does not).
block_extract() { # $1 = file
  awk -v begin="$MARK_BEGIN" -v end="$MARK_END" \
      -v lbegin="$LEGACY_MARK_BEGIN" -v lend="$LEGACY_MARK_END" '
    !inb && index($0, begin)  { inb=1; stop=end;   next }
    !inb && index($0, lbegin) { inb=1; stop=lend;  next }
    inb && index($0, stop) { exit }
    inb { print }
  ' "$1"
}

# Insert (at end) or replace the managed block in $1. Block text on stdin
# (written to $2 temp by caller for awk). Leaves $1 modified in place. A
# legacy-generation block is replaced in place by the current-generation block,
# which migrates the file without disturbing content around the block.
block_upsert() { # $1 = file (may be missing), $2 = block text file
  local file="$1" block="$2"
  if [ -e "$file" ] && block_present "$file"; then
    awk -v begin="$MARK_BEGIN" -v end="$MARK_END" \
        -v lbegin="$LEGACY_MARK_BEGIN" -v lend="$LEGACY_MARK_END" -v bf="$block" '
      !done && index($0, begin)  { done=1; stop=end;  skipline=1
                                  while ((getline line < bf) > 0) print line
                                  close(bf); next }
      !done && index($0, lbegin) { done=1; stop=lend; skipline=1
                                  while ((getline line < bf) > 0) print line
                                  close(bf); next }
      skipline { if (index($0, stop)) skipline=0; next }
      { print }
    ' "$file" > "$file.omd-tmp.$$" && mv -f "$file.omd-tmp.$$" "$file"
  elif [ -e "$file" ]; then
    cat "$file" > "$file.omd-tmp.$$"
    printf '\n' >> "$file.omd-tmp.$$"
    cat "$block" >> "$file.omd-tmp.$$"
    mv -f "$file.omd-tmp.$$" "$file"
  else
    cat "$block" > "$file"
  fi
}

# Remove the managed block (both marker lines inclusive) from $1, whether the
# file carries the current or the legacy marker generation.
block_remove() { # $1 = file
  [ -f "$1" ] || return 0
  block_present "$1" || return 0
  awk -v begin="$MARK_BEGIN" -v end="$MARK_END" \
      -v lbegin="$LEGACY_MARK_BEGIN" -v lend="$LEGACY_MARK_END" '
    !done && index($0, begin)  { done=1; stop=end;  skipline=1; next }
    !done && index($0, lbegin) { done=1; stop=lend; skipline=1; next }
    skipline { if (index($0, stop)) skipline=0; next }
    { print }
  ' "$1" > "$1.omd-tmp.$$" && mv -f "$1.omd-tmp.$$" "$1"
}
