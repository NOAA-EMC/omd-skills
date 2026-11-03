# formats.sh — instruction content transforms (research R7).
# shellcheck shell=bash
# Line-level frontmatter handling only: the catalog controls its own headers,
# every file has "---" fenced frontmatter starting at line 1 (verified policy:
# tests/test_repo_policy.py); body bytes are passed through untouched.

# Strip YAML frontmatter: print everything after the closing "---".
fm_strip() { # $1 = file
  awk '
    NR==1 && $0=="---" { infm=1; next }
    infm && $0=="---" { infm=0; next }
    !infm { print }
  ' "$1"
}

# Read one frontmatter scalar value (best effort, matches `key: value`).
fm_value() { # $1 = file $2 = key
  awk -v k="$2" '
    NR==1 && $0=="---" { infm=1; next }
    infm && $0=="---" { exit }
    infm {
      if (index($0, k ":") == 1) {
        v = substr($0, length(k) + 2)
        sub(/^[ \t]+/, "", v); sub(/[ \t\n]+$/, "", v)
        gsub(/^"|"$/, "", v)
        print v; exit
      }
    }
  ' "$1"
}

# Copilot delivery is verbatim: copy the source file unchanged.
emit_verbatim() { # $1 = source $2 = destination (already existing tree)
  cat "$1" > "$2"
}

# Cursor delivery: one .mdc frontmatter rewrite (applyTo: -> globs:;
# alwaysApply: false added; description and body preserved).
emit_mdc() { # $1 = source
  awk '
    NR==1 && $0=="---" { infm=1; print; next }
    infm && $0=="---" {
      infm=0
      if (!seen_globs) print "globs: \"**/*\""
      if (!seen_always) print "alwaysApply: false"
      print; next
    }
    infm {
      if ($0 ~ /^applyTo[ \t]*:/) {
        rest = $0; sub(/^applyTo[ \t]*:/, "", rest)
        print "globs:" rest
        seen_globs = 1
        next
      }
      if ($0 ~ /^alwaysApply[ \t]*:/) seen_always = 1
      print
      next
    }
    { print }
  ' "$1"
}
