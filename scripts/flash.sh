#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<'EOF'
flash.sh

Preparador rápido do host para gotchi.

Uso:
  sudo flash --all [--login-user USER]
  sudo ./scripts/flash.sh --all [--login-user USER]

Opções:
  --all                    instala dependências, gotchi nativo, config global, spool de cartas e opcionalmente snippet
  --login-user USER        usuário alvo para ativar o snippet opcional de login
  -h, --help               mostra esta ajuda
EOF
}

RUN_ALL="0"
LOGIN_USER=""

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --all)
        RUN_ALL="1"
        shift
        ;;
      --login-user)
        LOGIN_USER="$2"
        shift 2
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        echo "Opção desconhecida: $1" >&2
        usage
        exit 1
        ;;
    esac
  done
}

main() {
  parse_args "$@"

  if [[ "${RUN_ALL}" != "1" ]]; then
    echo "Erro: use --all para executar a preparação completa." >&2
    usage
    exit 1
  fi

  if [[ -n "${LOGIN_USER}" ]]; then
    bash "${SCRIPT_DIR}/install-system.sh" --global-config --enable-login-snippet --login-user "${LOGIN_USER}"
  else
    bash "${SCRIPT_DIR}/install-system.sh" --global-config
  fi
}

main "$@"
