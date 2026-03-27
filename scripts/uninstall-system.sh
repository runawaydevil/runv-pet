#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/gotchi}"
BIN_DIR="${BIN_DIR:-/usr/local/bin}"
MAIL_ROOT="${MAIL_ROOT:-/var/lib/gotchi-mail}"
REMOVE_GLOBAL_CONFIG="1"
REMOVE_LOGIN_SNIPPET="0"
REMOVE_LOGIN_SNIPPETS_ALL="0"
LOGIN_SNIPPET_USER=""
REMOVE_APP_DIR="1"
REMOVE_MAIL_ROOT="1"
PURGE_USER_STATE="0"

usage() {
  cat <<'EOF'
uninstall-system.sh

Remove a instalação nativa do gotchi e, opcionalmente, faz purge do estado dos usuários.

Uso:
  sudo ./scripts/uninstall-system.sh [opcoes]

Opções:
  --install-dir PATH           Diretório da aplicação. Default: /opt/gotchi
  --bin-dir PATH               Diretório dos launchers. Default: /usr/local/bin
  --mail-root PATH             Diretório do spool de cartas. Default: /var/lib/gotchi-mail
  --keep-app-dir               Mantém /opt/gotchi no disco
  --keep-global-config         Mantém /etc/xdg/gotchi/gotchi.json
  --keep-mail-root             Mantém o spool compartilhado de cartas
  --remove-login-snippet       Remove o snippet opcional do ~/.bashrc do usuário informado
  --remove-login-snippets-all  Remove o snippet opcional de todos os usuários locais
  --login-user USER            Usuário alvo para remover o snippet de login
  --purge-user-state           Remove diretórios e bancos do gotchi em todos os homes locais
  --purge-all                  Remove sistema, spool, config, snippets e estado dos usuários
  -h, --help                   Mostra esta ajuda
EOF
}

remove_launchers() {
  rm -f "${BIN_DIR}/gotchi"
  rm -f "${BIN_DIR}/flash"
}

remove_app_dir() {
  if [[ "${REMOVE_APP_DIR}" != "1" ]]; then
    return
  fi
  rm -rf "${INSTALL_DIR}"
}

remove_global_config() {
  if [[ "${REMOVE_GLOBAL_CONFIG}" != "1" ]]; then
    return
  fi

  rm -f /etc/xdg/gotchi/gotchi.json
  rmdir /etc/xdg/gotchi 2>/dev/null || true
}

remove_mail_root() {
  if [[ "${REMOVE_MAIL_ROOT}" != "1" ]]; then
    return
  fi

  rm -rf "${MAIL_ROOT}"
}

remove_login_snippet_from_home() {
  local bashrc="$1"
  if [[ ! -f "${bashrc}" ]]; then
    return
  fi

  python3 - <<PY
from pathlib import Path
path = Path(${bashrc@Q})
text = path.read_text(encoding="utf-8")
begin = "# >>> gotchi line >>>"
end = "# <<< gotchi line <<<"
start = text.find(begin)
finish = text.find(end)
if start != -1 and finish != -1 and finish > start:
    finish = text.find("\n", finish)
    if finish == -1:
        finish = len(text)
    else:
        finish += 1
    text = text[:start].rstrip() + "\n" + text[finish:].lstrip("\n")
    path.write_text(text, encoding="utf-8")
PY
}

remove_login_snippet() {
  if [[ "${REMOVE_LOGIN_SNIPPET}" != "1" ]]; then
    return
  fi

  if [[ -z "${LOGIN_SNIPPET_USER}" ]]; then
    echo "Erro: use --login-user USER junto com --remove-login-snippet" >&2
    exit 1
  fi

  local user_home
  user_home="$(getent passwd "${LOGIN_SNIPPET_USER}" | cut -d: -f6)"
  if [[ -z "${user_home}" ]]; then
    echo "Erro: usuário não encontrado: ${LOGIN_SNIPPET_USER}" >&2
    exit 1
  fi

  remove_login_snippet_from_home "${user_home}/.bashrc"
}

remove_login_snippets_all() {
  if [[ "${REMOVE_LOGIN_SNIPPETS_ALL}" != "1" ]]; then
    return
  fi

  while IFS=: read -r _name _pass _uid _gid _gecos home _shell; do
    [[ -n "${home}" ]] || continue
    [[ -d "${home}" ]] || continue
    remove_login_snippet_from_home "${home}/.bashrc"
  done < /etc/passwd
}

purge_user_state() {
  if [[ "${PURGE_USER_STATE}" != "1" ]]; then
    return
  fi

  while IFS=: read -r _name _pass _uid _gid _gecos home _shell; do
    [[ -n "${home}" ]] || continue
    [[ -d "${home}" ]] || continue
    rm -rf \
      "${home}/.local/state/gotchi" \
      "${home}/.config/gotchi" \
      "${home}/.local/share/gotchi" \
      "${home}/.gotchi-state" \
      "${home}/.gotchi-config" \
      "${home}/.gotchi-data"
  done < /etc/passwd
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --install-dir)
        INSTALL_DIR="$2"
        shift 2
        ;;
      --bin-dir)
        BIN_DIR="$2"
        shift 2
        ;;
      --mail-root)
        MAIL_ROOT="$2"
        shift 2
        ;;
      --keep-app-dir)
        REMOVE_APP_DIR="0"
        shift
        ;;
      --keep-global-config)
        REMOVE_GLOBAL_CONFIG="0"
        shift
        ;;
      --keep-mail-root)
        REMOVE_MAIL_ROOT="0"
        shift
        ;;
      --remove-login-snippet)
        REMOVE_LOGIN_SNIPPET="1"
        shift
        ;;
      --remove-login-snippets-all)
        REMOVE_LOGIN_SNIPPETS_ALL="1"
        shift
        ;;
      --login-user)
        LOGIN_SNIPPET_USER="$2"
        shift 2
        ;;
      --purge-user-state)
        PURGE_USER_STATE="1"
        shift
        ;;
      --purge-all)
        REMOVE_GLOBAL_CONFIG="1"
        REMOVE_MAIL_ROOT="1"
        REMOVE_LOGIN_SNIPPETS_ALL="1"
        PURGE_USER_STATE="1"
        shift
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
  remove_launchers
  remove_app_dir
  remove_global_config
  remove_mail_root
  remove_login_snippet
  remove_login_snippets_all
  purge_user_state

  cat <<EOF
Desinstalação concluída.

Removido:
  launcher: ${BIN_DIR}/gotchi
  flash: ${BIN_DIR}/flash
  app dir: ${INSTALL_DIR} $( [[ "${REMOVE_APP_DIR}" == "1" ]] && echo '(removido)' || echo '(mantido)' )
  config global: /etc/xdg/gotchi $( [[ "${REMOVE_GLOBAL_CONFIG}" == "1" ]] && echo '(removido)' || echo '(mantido)' )
  spool de cartas: ${MAIL_ROOT} $( [[ "${REMOVE_MAIL_ROOT}" == "1" ]] && echo '(removido)' || echo '(mantido)' )
  snippets de login globais: $( [[ "${REMOVE_LOGIN_SNIPPETS_ALL}" == "1" ]] && echo 'removidos' || echo 'mantidos' )
  estado dos usuarios: $( [[ "${PURGE_USER_STATE}" == "1" ]] && echo 'removido' || echo 'mantido' )

Observação:
  Use --purge-all quando quiser reverter tudo, incluindo saves e snippets dos usuários.
EOF
}

main "$@"
