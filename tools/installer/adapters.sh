# adapters.sh — agent profile table per contracts/installer-cli.md (research R3).
# shellcheck shell=bash
# Data functions only; sourced by install.sh.

ADAPTER_IDS="claude codex opencode gemini cursor copilot"

adapter_valid() {
  local id a
  for id in "$@"; do
    for a in $ADAPTER_IDS; do
      [ "$a" = "$id" ] && continue 2
    done
    return 1
  done
  return 0
}

# Project-relative skills dir; "" means the agent has no skills location.
adapter_skills_dir() {
  case "$1" in
    claude)                    printf '.claude/skills' ;;
    codex|opencode|gemini|cursor) printf '.agents/skills' ;;
    copilot)                   printf '.github/skills' ;;
    *) return 1 ;;
  esac
}

# Instruction delivery: '<mode>|<target>' where mode ∈ block|files|none.
adapter_instruction() {
  case "$1" in
    claude)          printf 'block|CLAUDE.md' ;;
    codex|opencode)  printf 'block|AGENTS.md' ;;
    gemini)          printf 'block|GEMINI.md' ;;
    cursor)          printf 'files|.cursor/rules|mdc' ;;
    copilot)         printf 'files|.github/instructions|verbatim' ;;
    *)               printf 'none|' ;;
  esac
}

# Paths whose presence in a project suggests this agent (interactive detect only;
# suggestions are always user-confirmed, research R8). Space-separated.
adapter_fingerprints() {
  case "$1" in
    claude)   printf '.claude CLAUDE.md' ;;
    codex)    printf '.agents AGENTS.md' ;;
    opencode) printf 'opencode.json opencode.jsonc' ;;
    gemini)   printf 'GEMINI.md .gemini' ;;
    cursor)   printf '.cursor' ;;
    copilot)  printf '.github/copilot-instructions.md .github/instructions .github/skills' ;;
    *)        printf '' ;;
  esac
}
