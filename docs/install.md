# Install on Debian 13

Este guia mostra como instalar e ativar o `gotchi` em um sistema Debian 13, pensando em um ambiente estilo runv.club.

## Modelo recomendado

O deploy nativo do sistema segue este layout:

- aplicacao isolada em `/opt/gotchi`
- virtualenv proprio em `/opt/gotchi/venv`
- source espelhado em `/opt/gotchi/source`
- scripts de manutencao em `/opt/gotchi/scripts`
- launcher global em `/usr/local/bin/gotchi`
- utilitario de preparacao em `/usr/local/bin/flash`
- spool root-only de cartas em `/var/lib/gotchi-mail`
- bridge setuid em `/opt/gotchi/bin/gotchi-mail-bridge`

Isso garante que:

- todo usuario novo do sistema ja tera acesso ao comando `gotchi`
- o comando nao depende de `~/.local/bin`
- o host nao depende do checkout original depois da instalacao
- os pets continuam separados por UID e independentes entre si
- o correio entre usuarios usa um backend central protegido, sem expor o banco diretamente aos usuarios

## Requisitos

Instale o basico:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv gcc
```

## Instalacao nativa do sistema

Instala o comando global para todos os usuarios:

```bash
sudo bash ./scripts/install-system.sh
```

Isso prepara:

- `/opt/gotchi`
- `/opt/gotchi/venv`
- `/opt/gotchi/source`
- `/opt/gotchi/scripts`
- `/usr/local/bin/gotchi`
- `/usr/local/bin/flash`
- `/var/lib/gotchi-mail`
- `/opt/gotchi/bin/gotchi-mail-bridge`

Opcoes uteis:

```bash
sudo bash ./scripts/install-system.sh --global-config
sudo bash ./scripts/install-system.sh --enable-login-snippet --login-user alice
sudo bash ./scripts/install-system.sh --global-config --enable-login-snippet --login-user alice
```

## Preparacao rapida com flash

Se quiser fazer tudo de uma vez:

```bash
sudo bash ./scripts/flash.sh --all
```

Ou ja instalar e ativar o aviso curto no login para um usuario especifico:

```bash
sudo bash ./scripts/flash.sh --all --login-user alice
```

O `flash --all` faz:

- instala dependencias base
- espelha o codigo necessario em `/opt/gotchi/source`
- instala o `gotchi` nativamente em `/opt/gotchi`
- compila e publica o bridge setuid de cartas
- publica `gotchi` em `/usr/local/bin`
- publica `flash` em `/usr/local/bin`
- cria o spool root-only de cartas em `/var/lib/gotchi-mail`
- cria config global base em `/etc/xdg/gotchi/gotchi.json`
- opcionalmente adiciona o snippet de login no `~/.bashrc` do usuario indicado

Depois do primeiro deploy, o atalho global tambem funciona assim:

```bash
sudo flash --all
sudo flash --all --login-user alice
```

## Comandos de deploy e administracao

Instalar no host:

```bash
sudo bash ./scripts/install-system.sh
sudo bash ./scripts/install-system.sh --global-config
sudo bash ./scripts/install-system.sh --enable-login-snippet --login-user alice
sudo bash ./scripts/install-system.sh --global-config --enable-login-snippet --login-user alice
```

Preparar tudo com o atalho global:

```bash
sudo bash ./scripts/flash.sh --all
sudo bash ./scripts/flash.sh --all --login-user alice
sudo flash --all
sudo flash --all --login-user alice
```

Checagem apos instalar:

```bash
which gotchi
which flash
gotchi help
gotchi path
gotchi doctor --storage
ls -ld /var/lib/gotchi-mail
ls -l /opt/gotchi/bin/gotchi-mail-bridge
```

Primeiro uso de um usuario:

```bash
gotchi init --name Nyx --species cat
gotchi status
gotchi feed
gotchi play
gotchi sleep
gotchi clean
gotchi rename Corvus
gotchi export ~/gotchi-backup.json
```

Migracao e diagnostico:

```bash
gotchi migrate
gotchi doctor --storage
gotchi path
```

Remocao do sistema:

```bash
sudo bash ./scripts/uninstall-system.sh
sudo bash ./scripts/uninstall-system.sh --keep-global-config --keep-mail-root
sudo bash ./scripts/uninstall-system.sh --remove-login-snippet --login-user alice
sudo bash ./scripts/uninstall-system.sh --remove-login-snippets-all
sudo bash ./scripts/uninstall-system.sh --purge-user-state
sudo bash ./scripts/uninstall-system.sh --purge-all
```

## Desinstalacao do sistema

```bash
sudo bash ./scripts/uninstall-system.sh
```

Opcionalmente:

```bash
sudo bash ./scripts/uninstall-system.sh --keep-global-config --keep-mail-root
sudo bash ./scripts/uninstall-system.sh --remove-login-snippet --login-user alice
sudo bash ./scripts/uninstall-system.sh --remove-login-snippets-all
sudo bash ./scripts/uninstall-system.sh --purge-user-state
sudo bash ./scripts/uninstall-system.sh --purge-all
```

Observacao:

- o desinstalador padrao remove o comando global, a app instalada, a config global e o spool de cartas
- ele preserva saves e snippets dos usuarios por padrao
- use `--purge-all` para rollback total, incluindo estado e snippets dos usuarios

## Primeiro uso

Cada usuario tera seu proprio pet privado e independente. Depois da instalacao global, qualquer conta pode fazer:

```bash
gotchi init --name Nyx --species cat
gotchi status
gotchi feed
gotchi sleep
```

## Ativacao opcional no login

Se quiser uma linha curta do pet ao abrir shell interativo, o instalador pode fazer isso automaticamente com `--enable-login-snippet --login-user USER`.

O bloco adicionado e:

```bash
case "$-" in
  *i*)
    command -v gotchi >/dev/null 2>&1 && gotchi line 2>/dev/null
    ;;
esac
```

Isso:

- so roda em shell interativo
- nao interfere em scripts
- e facil de remover

## Config padrao global opcional

Se quiser defaults globais para o host:

```bash
sudo bash ./scripts/install-system.sh --global-config
```

O arquivo base fica em:

```bash
/etc/xdg/gotchi/gotchi.json
```

Precedencia:

1. config global
2. config do usuario sobrescreve a global

## Diagnostico

Veja os caminhos efetivos:

```bash
gotchi path
```

Cheque storage e integridade:

```bash
gotchi doctor --storage
```

Se estiver migrando de versao antiga:

```bash
gotchi migrate
```

## Backup e restore

Exportar:

```bash
gotchi export ~/gotchi-backup.json
```

Importar:

```bash
gotchi import ~/gotchi-backup.json
```

## Testes locais

Se quiser validar o projeto antes do deploy:

```bash
python3 -m unittest discover -s tests -v
```
