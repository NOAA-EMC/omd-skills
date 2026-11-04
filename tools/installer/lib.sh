# lib.sh — shared helpers for omd-skills install.sh (sourced, not executable).
# shellcheck shell=bash
set -euo pipefail
unset CDPATH

die()  { printf 'install.sh: %s\n' "$1" >&2; exit "${2:-1}"; }
warn() { printf 'WARN: %s\n' "$1" >&2; }

# Usage text = leading comment block of the entry script (unpack.sh idiom).
usage_from() {
  awk '
    NR == 1 { next }
    /^#/ { sub(/^# ?/, ""); print; next }
    { exit }
  ' "$1"
}

# Resolve existing ancestor symlinks without GNU realpath; allow missing leaf.
canonical_dir() {
  local path="$1" parent base
  if [ -d "$path" ]; then
    (cd -P -- "$path" && pwd -P)
  else
    { [ ! -e "$path" ] && [ ! -L "$path" ]; } || die "not a directory: $path"
    parent="$(canonical_dir "$(dirname -- "$path")")" || exit 1
    base="$(basename -- "$path")"
    case "$base" in
      .) printf '%s\n' "$parent" ;;
      ..) dirname -- "$parent" ;;
      *) printf '%s/%s\n' "${parent%/}" "$base" ;;
    esac
  fi
}

# Fully resolve one path (following final symlinks too); prints canonical form.
resolve_path() {
  local t="$1" link dir
  while [ -L "$t" ]; do
    link="$(readlink "$t")"
    dir="$(dirname "$t")"
    case "$link" in
      /*) t="$link" ;;
      *)  t="$dir/$link" ;;
    esac
  done
  if [ -d "$t" ]; then canonical_dir "$t"; else
    dir="$(canonical_dir "$(dirname "$t")")"; printf '%s/%s\n' "${dir%/}" "$(basename "$t")"
  fi
}

# --- hashing -------------------------------------------------------------
_hash_impl=""
hash_init() {
  if command -v sha256sum >/dev/null 2>&1; then _hash_impl=sha256sum
  elif command -v shasum >/dev/null 2>&1; then _hash_impl=shasum
  else die "no sha256sum or shasum available to compute install hashes" 5
  fi
}
_h() { # hash stdin -> hex
  case "$_hash_impl" in
    sha256sum) sha256sum | cut -d' ' -f1 ;;
    shasum) shasum -a 256 | cut -d' ' -f1 ;;
  esac
}
file_hash() { # $1=file -> sha256:<hex>
  case "$_hash_impl" in
    sha256sum) printf 'sha256:%s' "$(sha256sum -- "$1" | cut -d' ' -f1)" ;;
    shasum) printf 'sha256:%s' "$(shasum -a 256 -- "$1" | cut -d' ' -f1)" ;;
  esac
}
# Aggregate over a tree: sorted relpaths + file digests (research R5).
_tree_rows() { # $1=canonical dir -> "relpath<TAB>digest" lines on stdout
  local f
  ( cd "$1" && find . -type f -print | LC_ALL=C sort | while IFS= read -r f; do
      printf '%s\t' "${f#./}"
      case "$_hash_impl" in
        sha256sum) sha256sum -- "$f" | cut -d' ' -f1 ;;
        shasum) shasum -a 256 -- "$f" | cut -d' ' -f1 ;;
      esac
      printf '\n'
    done )
}
tree_hash() { # $1=dir -> sha256:<hex> (sentinel for missing; callers guard)
  [ -d "$1" ] || { printf 'sha256:MISSING'; return; }
  local d
  d="$(cd -P -- "$1" && pwd -P)"
  printf 'sha256:%s' "$(_tree_rows "$d" | _h)"
}

now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# --- tiny JSON emitters (records we own; see contracts/install-record.md) --
json_str() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }

# --- tiny JSON line field readers (keys unique per generated line) --------
lock_field_str() { # $1=line $2=key -> value (keys unique per line; greedy last match)
  local pat out
  pat="s@.*\"$2\":\"\\([^\"]*\\)\".*@\\1@p"
  out="$(printf '%s' "$1" | sed -n "$pat" | head -n 1)"
  printf '%s' "$out" | sed -e 's/\\\\"/"/g' -e 's/\\\\/\\/g'
}

lock_field_bool() { # $1=line $2=key -> true|false
  printf '%s' "$1" | sed -nE "s/.*\"$2\":(true|false).*/\1/p"
}
lock_agents_has() { # $1=line $2=agent-id
  printf '%s' "$1" | grep -q "\"agents\":\\[[^]]*\"$2\""
}
lock_is_malformed() { # a usable lock line must carry type+path; nonzero rc => malformed
  printf '%s' "$1" | grep -q '"type":' && printf '%s' "$1" | grep -q '"path":'
}
idx_of() {
  local key="$1"; shift
  local i=0 item
  for item in "$@"; do
    [ "$item" = "$key" ] && { printf '%s' "$i"; return 0; }
    i=$((i + 1))
  done
  printf '4294967295'
  return 1
}

# csv_add CSV ITEM -> CSV with ITEM appended if absent (order kept)
csv_add() {
  local csv="$1" item="$2" existing
  for existing in $(printf '%s' "$csv" | tr ',' ' '); do
    [ "$existing" = "$item" ] && { printf '%s' "$csv"; return; }
  done
  if [ -z "$csv" ]; then printf '%s' "$item"; else printf '%s,%s' "$csv" "$item"; fi
}

csv_union() { # union of two TAB/comma-separated sets -> sorted comma list
  printf '%s,%s' "$1" "$2" | tr ',' '\n' | LC_ALL=C awk 'NF' | LC_ALL=C sort -u | paste -sd, -
}

idx_range() { # $1 = count -> list 0..count-1
  local i=0 n="$1"
  while [ "$i" -lt "$n" ]; do printf '%s ' "$i"; i=$((i+1)); done
}
