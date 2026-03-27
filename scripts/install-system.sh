#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

PYTHON_BIN="${PYTHON_BIN:-python3}"
INSTALL_DIR="${INSTALL_DIR:-/opt/gotchi}"
BIN_DIR="${BIN_DIR:-/usr/local/bin}"
SOURCE_DIR="${SOURCE_DIR:-${INSTALL_DIR}/source}"
MAIL_ROOT="${MAIL_ROOT:-/var/lib/gotchi-mail}"
INSTALL_DEPS="1"
INSTALL_GLOBAL_CONFIG="0"
ENABLE_LOGIN_SNIPPET="0"
LOGIN_SNIPPET_USER=""

usage() {
  cat <<'EOF'
install-system.sh

Instala o gotchi como comando nativo do sistema no Debian 13.

Layout padrão:
  app/venv em /opt/gotchi
  source espelhado em /opt/gotchi/source
  scripts de manutenção em /opt/gotchi/scripts
  launcher global em /usr/local/bin/gotchi
  atalho flash em /usr/local/bin/flash
  spool de cartas root-only em /var/lib/gotchi-mail
  bridge setuid em /opt/gotchi/bin/gotchi-mail-bridge

Uso:
  sudo ./scripts/install-system.sh [opcoes]

Opções:
  --python PATH              Binário Python a usar. Default: python3
  --install-dir PATH         Diretório da aplicação. Default: /opt/gotchi
  --bin-dir PATH             Diretório dos launchers. Default: /usr/local/bin
  --mail-root PATH           Diretório do spool de cartas. Default: /var/lib/gotchi-mail
  --skip-deps                Não roda apt install
  --global-config            Gera /etc/xdg/gotchi/gotchi.json se ainda não existir
  --enable-login-snippet     Instala snippet opcional em ~/.bashrc do usuário informado
  --login-user USER          Usuário alvo do snippet de login
  -h, --help                 Mostra esta ajuda
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Erro: comando ausente: $1" >&2
    exit 1
  fi
}

install_dependencies() {
  if [[ "${INSTALL_DEPS}" != "1" ]]; then
    return
  fi

  require_cmd apt-get
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y python3 python3-pip python3-venv gcc
}

prepare_layout() {
  install -d -m 0755 "${INSTALL_DIR}" "${INSTALL_DIR}/bin" "${INSTALL_DIR}/scripts" "${SOURCE_DIR}" "${BIN_DIR}"
}

prepare_mail_root() {
  install -d -m 0700 "${MAIL_ROOT}"
  touch "${MAIL_ROOT}/mail.db" "${MAIL_ROOT}/mail.lock"
  chmod 0600 "${MAIL_ROOT}/mail.db" "${MAIL_ROOT}/mail.lock"
}

sync_source_tree() {
  if [[ ! -f "${ROOT_DIR}/pyproject.toml" ]]; then
    echo "Erro: pyproject.toml não encontrado em ${ROOT_DIR}" >&2
    exit 1
  fi

  rm -rf "${SOURCE_DIR}"
  install -d -m 0755 "${SOURCE_DIR}"

  tar \
    --exclude='.git' \
    --exclude='.test-artifacts' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -C "${ROOT_DIR}" \
    -cf - pyproject.toml README.md src docs 2>/dev/null | tar -C "${SOURCE_DIR}" -xf -

  install -m 0755 "${ROOT_DIR}/scripts/install-system.sh" "${INSTALL_DIR}/scripts/install-system.sh"
  install -m 0755 "${ROOT_DIR}/scripts/uninstall-system.sh" "${INSTALL_DIR}/scripts/uninstall-system.sh"
  install -m 0755 "${ROOT_DIR}/scripts/flash.sh" "${INSTALL_DIR}/scripts/flash.sh"
  install -m 0644 "${ROOT_DIR}/scripts/gotchi-mail-bridge.c" "${INSTALL_DIR}/scripts/gotchi-mail-bridge.c"
}

create_venv() {
  if [[ ! -x "${INSTALL_DIR}/venv/bin/python" ]]; then
    "${PYTHON_BIN}" -m venv "${INSTALL_DIR}/venv"
  fi
}

install_package() {
  cd "${SOURCE_DIR}"
  "${INSTALL_DIR}/venv/bin/python" -m pip install --upgrade pip setuptools wheel
  "${INSTALL_DIR}/venv/bin/python" -m pip install --upgrade .
}

build_mail_bridge() {
  local compiler=""
  if command -v cc >/dev/null 2>&1; then
    compiler="cc"
  elif command -v gcc >/dev/null 2>&1; then
    compiler="gcc"
  else
    echo "Erro: compilador C ausente (cc/gcc)." >&2
    exit 1
  fi

  "${compiler}" \
    -O2 \
    -DHELPER_PYTHON='"'"${INSTALL_DIR}/venv/bin/python"'"' \
    -DHELPER_MAIL_ROOT='"'"${MAIL_ROOT}"'"' \
    -DHELPER_MODULE='"gotchi_app.mail_helper"' \
    -o "${INSTALL_DIR}/bin/gotchi-mail-bridge" \
    "${INSTALL_DIR}/scripts/gotchi-mail-bridge.c"

  chown root:root "${INSTALL_DIR}/bin/gotchi-mail-bridge"
  chmod 4755 "${INSTALL_DIR}/bin/gotchi-mail-bridge"
  "${INSTALL_DIR}/bin/gotchi-mail-bridge" init >/dev/null
}

install_launchers() {
  cat > "${INSTALL_DIR}/bin/gotchi" <<EOF
#!/usr/bin/env bash
exec "${INSTALL_DIR}/venv/bin/gotchi" "\$@"
EOF
  chmod 0755 "${INSTALL_DIR}/bin/gotchi"
  ln -sfn "${INSTALL_DIR}/bin/gotchi" "${BIN_DIR}/gotchi"

  cat > "${INSTALL_DIR}/bin/flash" <<EOF
#!/usr/bin/env bash
exec "${INSTALL_DIR}/scripts/flash.sh" "\$@"
EOF
  chmod 0755 "${INSTALL_DIR}/bin/flash"
  ln -sfn "${INSTALL_DIR}/bin/flash" "${BIN_DIR}/flash"
}

ensure_global_config() {
  if [[ "${INSTALL_GLOBAL_CONFIG}" != "1" ]]; then
    return
  fi

  local target_dir="/etc/xdg/gotchi"
  local target_file="${target_dir}/gotchi.json"
  mkdir -p "${target_dir}"
  if [[ ! -f "${target_file}" ]]; then
    cat > "${target_file}" <<'EOF'
{
  "hunger_per_hour": 6.0,
  "energy_loss_per_hour": 4.5,
  "hygiene_loss_per_hour": 3.0,
  "sleep_energy_gain_per_hour": 11.0,
  "sleep_hunger_per_hour": 4.0,
  "mood_recovery_per_hour": 1.5,
  "mood_penalty_per_hour": 2.0,
  "health_penalty_per_hour": 3.0,
  "health_recovery_per_hour": 0.8,
  "illness_threshold": 35.0,
  "death_threshold_hours": 36.0,
  "max_stat": 100.0
}
EOF
    chmod 0644 "${target_file}"
  fi
}

enable_login_snippet() {
  if [[ "${ENABLE_LOGIN_SNIPPET}" != "1" ]]; then
    return
  fi

  if [[ -z "${LOGIN_SNIPPET_USER}" ]]; then
    echo "Erro: use --login-user USER junto com --enable-login-snippet" >&2
    exit 1
  fi

  local user_home
  user_home="$(getent passwd "${LOGIN_SNIPPET_USER}" | cut -d: -f6)"
  if [[ -z "${user_home}" ]]; then
    echo "Erro: usuário não encontrado: ${LOGIN_SNIPPET_USER}" >&2
    exit 1
  fi

  local bashrc="${user_home}/.bashrc"
  local marker_begin="# >>> gotchi line >>>"
  local marker_end="# <<< gotchi line <<<"

  touch "${bashrc}"
  if ! grep -Fq "${marker_begin}" "${bashrc}"; then
    cat >> "${bashrc}" <<EOF

${marker_begin}
case "\$-" in
  *i*)
    command -v gotchi >/dev/null 2>&1 && gotchi line 2>/dev/null
    ;;
esac
${marker_end}
EOF
  fi

  chown "${LOGIN_SNIPPET_USER}:${LOGIN_SNIPPET_USER}" "${bashrc}" || true
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --python)
        PYTHON_BIN="$2"
        shift 2
        ;;
      --install-dir)
        INSTALL_DIR="$2"
        SOURCE_DIR="$2/source"
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
      --skip-deps)
        INSTALL_DEPS="0"
        shift
        ;;
      --global-config)
        INSTALL_GLOBAL_CONFIG="1"
        shift
        ;;
      --enable-login-snippet)
        ENABLE_LOGIN_SNIPPET="1"
        shift
        ;;
      --login-user)
        LOGIN_SNIPPET_USER="$2"
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
  require_cmd "${PYTHON_BIN}"
  require_cmd tar
  install_dependencies
  prepare_layout
  prepare_mail_root
  sync_source_tree
  create_venv
  install_package
  build_mail_bridge
  install_launchers
  ensure_global_config
  enable_login_snippet

  cat <<EOF
Instalação concluída.

Layout:
  app: ${INSTALL_DIR}
  source espelhado: ${SOURCE_DIR}
  scripts de manutenção: ${INSTALL_DIR}/scripts
  comando global: ${BIN_DIR}/gotchi
  utilitário flash: ${BIN_DIR}/flash
  spool de cartas: ${MAIL_ROOT}
  bridge setuid: ${INSTALL_DIR}/bin/gotchi-mail-bridge

Próximos passos:
  gotchi help
  gotchi path
  gotchi init --name Nyx --species cat

Diagnóstico:
  gotchi doctor --storage
EOF
}

main "$@"
