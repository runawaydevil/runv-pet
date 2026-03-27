from __future__ import annotations

import textwrap
from datetime import datetime, timezone

from .models import Pet
from .runv_mode import ServerPetStatus
from .simulator import general_status, normalize_species
from .storage import MigrationReport, StorageDoctorReport


PET_ART = {
    "cat": {
        "happy": r"""
 /\_/\\
( o.o )
 > ^ <
""".strip("\n"),
        "sleep": r"""
 /\_/\\
( -.- ) z
 > ^ <
""".strip("\n"),
        "tired": r"""
 /\_/\\
( -.- )
 > ^ <
""".strip("\n"),
        "sick": r"""
 /\_/\\
( x.x )
 > ^ <
""".strip("\n"),
        "dead": r"""
 /\_/\\
( _._ )
 > ^ <
""".strip("\n"),
    },
    "fox": {
        "happy": r"""
 /\   /\\
((ovo ))
():::()
  V V
""".strip("\n"),
        "sleep": r"""
 /\   /\\
((uvu )) z
():::()
  V V
""".strip("\n"),
        "tired": r"""
 /\   /\\
((-v- ))
():::()
  V V
""".strip("\n"),
        "sick": r"""
 /\   /\\
((xvx ))
():::()
  V V
""".strip("\n"),
        "dead": r"""
 /\   /\\
((___ ))
():::()
  V V
""".strip("\n"),
    },
    "dog": {
        "happy": r"""
 / \__
(    @\___
 /         O
/   (_____/
/_____/   U
""".strip("\n"),
        "sleep": r"""
 / \__
(    -\___ z
 /         O
/   (_____/
/_____/   U
""".strip("\n"),
        "tired": r"""
 / \__
(    -\___
 /         O
/   (_____/
/_____/   U
""".strip("\n"),
        "sick": r"""
 / \__
(    x\___
 /         O
/   (_____/
/_____/   U
""".strip("\n"),
        "dead": r"""
 / \__
(    _\___
 /         O
/   (_____/
/_____/   U
""".strip("\n"),
    },
    "crow": {
        "happy": r"""
   \
   (o>
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "sleep": r"""
   \
   (u>   z
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "tired": r"""
   \
   (-<
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "sick": r"""
   \
   (x<
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "dead": r"""
   \
   (_x)
\\_//)
 \_/_
  _|_
""".strip("\n"),
    },
    "raven": {
        "happy": r"""
   \
   (O>
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "sleep": r"""
   \
   (U>   z
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "tired": r"""
   \
   (-<
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "sick": r"""
   \
   (x<
\\_//)
 \_/_
  _|_
""".strip("\n"),
        "dead": r"""
   \
   (_x)
\\_//)
 \_/_
  _|_
""".strip("\n"),
    },
    "owl": {
        "happy": r"""
  ,_,
 (O,O)
 (   )
  " "
""".strip("\n"),
        "sleep": r"""
  ,_,
 (-,-) z
 (   )
  " "
""".strip("\n"),
        "tired": r"""
  ,_,
 (-,-)
 (   )
  " "
""".strip("\n"),
        "sick": r"""
  ,_,
 (x,x)
 (   )
  " "
""".strip("\n"),
        "dead": r"""
  ,_,
 (_,_)
 (   )
  " "
""".strip("\n"),
    },
    "blob": {
        "happy": r"""
  .-.
 (o o)
 | O \
  \   \
   `~~~'
""".strip("\n"),
        "sleep": r"""
  .-.
 (- -) z
 | O \
  \   \
   `~~~'
""".strip("\n"),
        "tired": r"""
  .-.
 (- -)
 | O \
  \   \
   `~~~'
""".strip("\n"),
        "sick": r"""
  .-.
 (x x)
 | O \
  \   \
   `~~~'
""".strip("\n"),
        "dead": r"""
  .-.
 (_ _)
 | O \
  \   \
   `~~~'
""".strip("\n"),
    },
}


RUNV_ART = {
    "excelente": r"""
    _
   \\
   (O>
\\_//)
 \_/_
  / \\
""".strip("\n"),
    "bem": r"""
    _
   \\
   (o>
\\_//)
 \_/_
  / \\
""".strip("\n"),
    "atencao": r"""
    _
   \\
   (-<
\\_//)
 \_/_
  / \\
""".strip("\n"),
    "critico": r"""
    _
   \\
   (x<
\\_//)
 \_/_
  / \\
""".strip("\n"),
}


def pick_art(pet: Pet) -> str:
    species = normalize_species(pet.species)
    art = PET_ART.get(species, PET_ART["blob"])
    if not pet.alive:
        return art["dead"]
    if pet.is_sleeping:
        return art["sleep"]
    if pet.illness or pet.health < 35:
        return art["sick"]
    if pet.energy < 35 or pet.mood < 35:
        return art["tired"]
    return art["happy"]


def bar(label: str, value: float, invert: bool = False, width: int = 22) -> str:
    shown = 100.0 - value if invert else value
    shown = max(0.0, min(100.0, shown))
    filled = round((shown / 100.0) * width)
    meter = "#" * filled + "-" * (width - filled)
    return f"{label:>9} [{meter}] {shown:5.1f}"


def human_delta(from_dt: datetime, to_dt: datetime) -> str:
    delta = max(0, int((to_dt - from_dt).total_seconds()))
    hours, rem = divmod(delta, 3600)
    minutes, _ = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _pet_hint(pet: Pet) -> str:
    if not pet.alive:
        return "O ciclo deste companheiro terminou."
    if pet.illness or pet.health < 40:
        return "Sugestao: `gotchi doctor` e depois um pouco de descanso."
    if pet.hunger > 70:
        return "Sugestao: `gotchi feed` antes que o humor piore."
    if pet.energy < 35:
        return "Sugestao: `gotchi sleep` para recuperar energia."
    if pet.hygiene < 40:
        return "Sugestao: `gotchi clean` para colocar tudo em ordem."
    if pet.mood < 45:
        return "Sugestao: `gotchi play` para animar o ambiente."
    return "Tudo em ordem. Um pouco de cuidado de vez em quando ja mantem o pet feliz."


def status_screen(pet: Pet, now: datetime) -> str:
    utc_now = now.astimezone(timezone.utc)
    created = pet.created_at.astimezone(timezone.utc)
    interaction = pet.last_interaction_at.astimezone(timezone.utc)
    lines = [
        "gotchi // habitat",
        f"{pet.name} [{pet.species}]",
        pick_art(pet),
        (
            f"Estado: {general_status(pet)} | Saude: {'doente' if pet.illness else 'estavel'} "
            f"| Vida: {'ativo' if pet.alive else 'encerrado'} | Sono: {'dormindo' if pet.is_sleeping else 'acordado'}"
        ),
        bar("fome", pet.hunger),
        bar("energia", pet.energy),
        bar("humor", pet.mood),
        bar("higiene", pet.hygiene),
        bar("saude", pet.health),
        "",
        textwrap.fill(pet.last_message, width=72),
        textwrap.fill(_pet_hint(pet), width=72),
        "",
        f"Idade: {pet.age_hours / 24.0:.1f} dias | Criado ha: {human_delta(created, utc_now)}",
        f"Ultima interacao: {human_delta(interaction, utc_now)} atras",
        f"Ultimo update: {pet.last_update_at.isoformat()}",
        "",
        "Acoes: init | status | path | line | feed | play | sleep | clean | rename NOVO_NOME | doctor | migrate | export | import | help",
    ]
    if pet.cause_of_death:
        lines.insert(5, f"Causa da morte: {pet.cause_of_death}")
    return "\n".join(lines)


def runv_status_screen(status: ServerPetStatus) -> str:
    detail_map = {
        "excelente": "estavel",
        "bem": "calmo",
        "atencao": "sensivel",
        "critico": "hostil",
    }
    lines = [
        "runv // observatorio",
        "corvo do servidor",
        RUNV_ART[status.status],
        f"Estado geral: {status.status} | Ninho: {status.perch}",
        f"Ritmo do ar: {detail_map[status.load_state]}",
        f"Poleiro de dados: {detail_map[status.disk_state]}",
        f"Trilha de escrita: {detail_map[status.write_state]}",
        "",
        textwrap.fill(status.message, width=72),
        textwrap.fill("Este corvo nao aceita comandos. Ele so observa o humor do ninho.", width=72),
    ]
    return "\n".join(lines)


def path_screen(report: dict[str, str]) -> str:
    lines = ["gotchi // path", ""]
    for key in (
        "uid",
        "username",
        "home",
        "state_dir",
        "config_dir",
        "data_dir",
        "save_path",
        "lock_path",
        "config_path",
        "global_config_path",
    ):
        if key in report:
            lines.append(f"{key:>18}: {report[key]}")
    return "\n".join(lines)


def doctor_storage_screen(report: StorageDoctorReport) -> str:
    lines = [
        "gotchi // storage doctor",
        "",
        f"resultado: {'ok' if report.ok else 'problemas encontrados'}",
        f"save_path: {report.save_path}",
        f"lock_path: {report.lock_path}",
        "",
    ]
    lines.extend(report.checks)
    return "\n".join(lines)


def migration_screen(report: MigrationReport) -> str:
    lines = ["gotchi // migrate", "", report.message]
    if report.source_path is not None:
        lines.append(f"origem: {report.source_path}")
    if report.backup_path is not None:
        lines.append(f"backup: {report.backup_path}")
    return "\n".join(lines)


def status_line(pet: Pet) -> str:
    if not pet.alive:
        return f"{pet.name} se foi. O habitat ficou silencioso."
    hunger_band = "atencao" if pet.hunger >= 70 else "ok"
    mood_band = "otimo" if pet.mood >= 75 else "instavel" if pet.mood < 45 else "bom"
    if pet.is_sleeping:
        return f"{pet.name} dormiu bem. Humor: {mood_band}."
    return f"{pet.name} esta por perto. Fome: {hunger_band}. Humor: {mood_band}."


def help_text() -> str:
    return textwrap.dedent(
        """
        gotchi: bichinho virtual de terminal para comunidades pubnix.

        Comandos:
          gotchi                 abre a tela textual principal
          gotchi init            cria seu pet
          gotchi status          mostra o estado atual
          gotchi path            mostra caminhos e identidade efetiva
          gotchi line            mostra uma linha curta para login/shell
          gotchi feed            alimenta o pet
          gotchi play            brinca com o pet
          gotchi sleep           coloca o pet para dormir
          gotchi clean           limpa o pet
          gotchi rename NOME     renomeia o pet
          gotchi doctor          tenta tratar doenca / recuperar saude
          gotchi doctor --storage verifica storage, migracao e integridade
          gotchi migrate         tenta migrar save legado
          gotchi export [ARQ]    exporta o pet atual em JSON
          gotchi import ARQ      importa backup do proprio usuario
          gotchi help            mostra esta ajuda

        Sem daemon:
          O estado e recalculado pelo tempo decorrido desde o ultimo update.

        desenvolvido por admin@runv.club
        """
    ).strip()
