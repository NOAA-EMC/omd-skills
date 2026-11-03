# record.sh — .ompd/genesis.lock JSONL + staging tree I/O (research R5).
# shellcheck shell=bash
# Physical format: specs/001-multi-agent-installer/contracts/install-record.md.

# LOCK_FILE/STAGE_DIR are set by install.sh from OMPD_DIR before sourcing.

# Globals set by record_load:
LOCK_LINES=()   # raw JSONL lines
LOCK_PATHS=()   # parallel: path per line

record_load() {
  LOCK_LINES=(); LOCK_PATHS=()
  [ -f "$LOCK_FILE" ] || return 0
  local line
  while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    lock_is_malformed "$line" || \
      die "install record $LOCK_FILE contains a malformed line; repair or remove it and re-run" 4
    LOCK_LINES+=("$line")
    LOCK_PATHS+=("$(lock_field_str "$line" path)")
  done < "$LOCK_FILE"
}

record_find_line() { # $1 = path -> echo line, rc1 absent
  local i
  i="$(idx_of "$1" "${LOCK_PATHS[@]+"${LOCK_PATHS[@]}"}")" || return 1
  [ "$i" = "4294967295" ] && return 1
  printf '%s\n' "${LOCK_LINES[$i]}"
}

record_has() { record_find_line "$1" >/dev/null; }

# --- entry emitters ------------------------------------------------------
record_json_skill() { # path agents_csv source mode hash created
  printf '{"v":1,"type":"skill","path":"%s","agents":[%s],"source":"%s","mode":"%s","content_hash":"%s","created":%s,"ts":"%s"}\n' \
    "$(json_str "$1")" "$(record_json_agents "$2")" "$(json_str "$3")" "$4" "$5" "$6" "$(now_iso)"
}
record_json_instruction_file() { # path agents_csv source format hash created
  printf '{"v":1,"type":"instruction-file","path":"%s","agents":[%s],"source":"%s","format":"%s","mode":"copy","content_hash":"%s","created":%s,"ts":"%s"}\n' \
    "$(json_str "$1")" "$(record_json_agents "$2")" "$(json_str "$3")" "$4" "$5" "$6" "$(now_iso)"
}
record_json_rules_block() { # path agents_csv source_json block_hash preimage created
  printf '{"v":1,"type":"rules-block","path":"%s","agents":[%s],"source":%s,"block_hash":"%s","preimage_hash":"%s","created":%s,"ts":"%s"}\n' \
    "$(json_str "$1")" "$(record_json_agents "$2")" "$3" "$4" "$5" "$6" "$(now_iso)"
}
record_json_agents() { # "a,b" -> "\"a\",\"b\"" (validated ids only, no escaping needed)
  printf '%s' "$1" | sed -e 's/^/"/' -e 's/,/","/g' -e 's/$/"/'
}

# --- locking & commit ------------------------------------------------------
lock_refuse_foreign() { # .ompd exists but is not ours => never touched
  [ -e "$OMPD_DIR" ] || return 0
  [ -f "$LOCK_FILE" ] && return 0
  # No lock yet: tolerate an empty dir or our own staging skeleton.
  local entry base ok=1
  for entry in "$OMPD_DIR"/* "$OMPD_DIR"/.[!.]* "$OMPD_DIR"/..?*; do
    [ -e "$entry" ] || continue            # unmatched glob literal
    base="$(basename "$entry")"
    [ "$base" = "genesis.lock.d" ] && continue
    ok=0
  done
  [ "$ok" = 1 ] && return 0
  die "$OMPD_DIR exists and was not created by this installer; refusing to manage it" 3
}

lock_commit() { # $1 = newline-separated lines file; atomic temp+mv
  mkdir -p "$OMPD_DIR" "$STAGE_DIR"
  local tmp="$LOCK_FILE.tmp.$$"
  sort "$1" > "$tmp"   # deterministic order for byte-compare parity tests (SC-005); ts differs by design
  mv -f "$tmp" "$LOCK_FILE"
}

lock_teardown() { # remove state dir entirely when empty
  if [ ! -s "$LOCK_FILE" ] || [ ! -f "$LOCK_FILE" ]; then
    [ -f "$LOCK_FILE" ] && [ -s "$LOCK_FILE" ] && return 0
    rm -Rf "$OMPD_DIR"
  fi
}

# --- staging ----------------------------------------------------------------
stage_clear_skill() { rm -Rf "$STAGE_DIR/skills/$1"; }

stage_sync_skill() { # $1 = skill name, $2 = source dir (verbatim copy)
  local dest="$STAGE_DIR/skills/$1"
  rm -Rf "$dest"
  mkdir -p "$dest"
  cp -R "$2/." "$dest/"
}

stage_file() { # $1 = staged relative name under instructions/, $2 = src file
  mkdir -p "$STAGE_DIR/instructions"
  cp -f "$2" "$STAGE_DIR/instructions/$1"
}

unstage_file_like() { # remove one staged thing, best effort
  rm -f "$STAGE_DIR/$1" 2>/dev/null || true
}

staged_skill_path() { printf '%s\n' "$STAGE_DIR/skills/$1"; }
