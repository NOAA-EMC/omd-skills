# catalog.sh — discovery of catalog leaves + instruction inventory.
# shellcheck shell=bash
# Leaf walk rules are identical to unpack.sh (research R2/FR-016 parity):
# stop at first SKILL.md, skip hidden dirs, refuse symlinked catalog dirs.

# $1 = catalog skills root, $2 = domain filter ("*" = all)
discover_leaves() {
  local root="$1" filter="$2"
  _leaf_walk() {
    local dir="$1" child name
    for child in "$dir"/*/; do
      [ -d "$child" ] || continue
      [ ! -L "${child%/}" ] || die "symlinked catalog directory: ${child%/}" 5
      name="$(basename "$child")"
      case "$name" in .*) continue ;; esac
      if [ -f "$child/SKILL.md" ]; then
        printf '%s\t%s\t%s\n' "$(basename "$dir")" "$name" "${child%/}"
      else
        _leaf_walk "${child%/}"
      fi
    done
  }
  local domain entry
  [ -d "$root" ] || die "skills/ not found in catalog copy ($root)" 5
  for entry in "$root"/*/; do
    [ -d "$entry" ] || continue
    [ ! -L "${entry%/}" ] || die "symlinked catalog directory: ${entry%/}" 5
    domain="$(basename "$entry")"
    case "$domain" in .*) continue ;; esac
    if [ "$filter" != "*" ] && [ "$filter" != "$domain" ]; then
      [ -f "$entry/SKILL.md" ] || continue
    fi
    if [ -f "$entry/SKILL.md" ]; then
      if [ "$filter" = "*" ] || [ "$filter" = "$domain" ]; then
        printf '%s\t%s\t%s\n' "(flat)" "$domain" "${entry%/}"
      fi
      continue
    fi
    if [ "$filter" = "*" ] || [ "$filter" = "$domain" ]; then
      _leaf_walk "${entry%/}"
    fi
  done | awk -F'\t' -v f="$filter" '
    f != "*" && $1 == "(flat)" && $2 != f { next }
    { print }
  '
}

# Global duplicate-name guard (mirrors unpack.sh "duplicate skill name(s)
# across domains" error; exit 5 per data-model E1 validation).
validate_unique_names() { # $1 = rows
  local dups
  dups="$(printf '%s' "$1" | cut -f2 | sort | uniq -d || true)"
  [ -z "$dups" ] || die "duplicate skill name(s) across domains: $(printf '%s' "$dups" | tr '\n' ' ')" 5
}

# Instruction inventory: one path per line.
discover_instructions() {
  local idir="$1" f
  for f in "$idir"/*.instructions.md; do
    [ -f "$f" ] || continue
    printf '%s\n' "$f"
  done
}

inst_name() { basename "$1" | sed 's/\.instructions\.md$//'; }

# FR-014: domain-level license/notice material belongs with every flattened
# leaf of that domain (copy mode). Flat skills carry their own LICENSE inside
# the leaf and need no overlay.
extras_for_leaf() { # $1 = leaf dir -> newline list of applicable extra files
  local leaf="$1" dom f base
  dom="$(dirname "$leaf")"
  [ "$(basename "$dom")" = "skills" ] && return 0
  for f in "$dom"/LICENSE* "$dom"/NOTICE* "$dom"/ATTRIBUTION*; do
    [ -f "$f" ] || continue
    base="$(basename "$f")"
    [ -e "$leaf/$base" ] && continue
    printf '%s\n' "$f"
  done
}
