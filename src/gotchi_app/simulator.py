from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from .config import Tuning
from .models import Pet


SPECIES = ("cat", "fox", "dog", "crow", "raven", "owl", "blob")


SPECIES_ALIASES = {
    "bird": "crow",
    "kitty": "cat",
    "kitten": "cat",
    "puppy": "dog",
    "wolf": "dog",
}


@dataclass(frozen=True)
class SpeciesFlavor:
    arrival: str
    healthy: str
    okay: str
    warning: str
    sleeping: str
    sick: str
    dead: str
    feed: str
    play: str
    sleep: str
    sleep_again: str
    clean: str
    doctor: str
    doctor_ok: str


SPECIES_FLAVOR = {
    "cat": SpeciesFlavor(
        arrival="Saltou para o terminal como se sempre tivesse morado aqui.",
        healthy="{name} observa tudo com a calma arrogante de quem manda no teclado.",
        okay="{name} segue bem, mas aceita carinho e um pouco de atencao.",
        warning="{name} esfrega no prompt pedindo cuidado.",
        sleeping="{name} dorme enrolado perto do cursor.",
        sick="{name} parece abatido e precisa de cuidado.",
        dead="O cantinho de {name} ficou quieto demais.",
        feed="{name} comeu satisfeito e ficou ronronando por perto.",
        play="{name} perseguiu sombras no terminal e voltou animado.",
        sleep="{name} se enrolou para dormir em paz.",
        sleep_again="{name} ja esta dormindo. Melhor deixar descansar.",
        clean="{name} saiu limpo, alinhado e com o pelo em ordem.",
        doctor="{name} recebeu cuidados e parece bem mais confortavel.",
        doctor_ok="{name} nao precisava de medico, mas aprovou a consulta.",
    ),
    "fox": SpeciesFlavor(
        arrival="Chegou leve e atento, como se ja conhecesse cada canto do shell.",
        healthy="{name} circula pelo terminal com energia e curiosidade.",
        okay="{name} esta bem, mas quer um pouco mais de presenca.",
        warning="{name} anda inquieto e quer atencao.",
        sleeping="{name} dorme com a cauda cobrindo o focinho.",
        sick="{name} perdeu o brilho e precisa de cuidado.",
        dead="O rastro de {name} sumiu do terminal.",
        feed="{name} comeu bem e voltou alerta.",
        play="{name} disparou pelo terminal e voltou com os olhos brilhando.",
        sleep="{name} se recolheu para um sono leve.",
        sleep_again="{name} ja esta dormindo. Melhor nao interromper.",
        clean="{name} ajeitou o pelo e ficou pronto para mais uma volta.",
        doctor="{name} recebeu cuidados e voltou a se firmar.",
        doctor_ok="{name} estava bem, mas aceitou o check-up com elegancia.",
    ),
    "dog": SpeciesFlavor(
        arrival="Entrou abanando o rabo e adotou o terminal na hora.",
        healthy="{name} esta feliz e pronto para acompanhar cada comando.",
        okay="{name} esta bem, mas topa companhia e brincadeira.",
        warning="{name} anda carente e nao quer ficar de lado.",
        sleeping="{name} dorme tranquilo, guardando o terminal.",
        sick="{name} parece cansado e precisa de ajuda.",
        dead="O lugar de {name} ficou silencioso.",
        feed="{name} comeu com vontade e ficou contente.",
        play="{name} correu, pulou e voltou ofegante e feliz.",
        sleep="{name} deitou para descansar por um tempo.",
        sleep_again="{name} ja esta dormindo. Melhor deixar quieto.",
        clean="{name} ficou limpo e bem mais confortavel.",
        doctor="{name} recebeu cuidados e voltou a animar.",
        doctor_ok="{name} nao precisava de medico, mas gostou da atencao.",
    ),
    "crow": SpeciesFlavor(
        arrival="Pousou no terminal e tomou posse do espaco.",
        healthy="{name} observa tudo com inteligencia suspeita.",
        okay="{name} segue firme, mas quer um agrado.",
        warning="{name} bate o bico no prompt pedindo presenca.",
        sleeping="{name} dorme empoleirado, um olho quase aberto.",
        sick="{name} arrepia as penas e precisa de cuidado.",
        dead="O poleiro de {name} ficou quieto.",
        feed="{name} comeu bem e voltou a vigiar o terminal.",
        play="{name} fez rasantes curtos e voltou satisfeito.",
        sleep="{name} se encolheu para tirar um sono leve.",
        sleep_again="{name} ja esta dormindo. Melhor nao mexer.",
        clean="{name} alinhou as penas e ficou bem mais apresentavel.",
        doctor="{name} recebeu cuidados e voltou a firmar o olhar.",
        doctor_ok="{name} nao precisava de medico, mas aceitou a visita com dignidade.",
    ),
    "raven": SpeciesFlavor(
        arrival="Chegou em silencio e assumiu o terminal como territorio.",
        healthy="{name} mantém um olhar atento sobre cada linha do shell.",
        okay="{name} esta bem, mas nao recusaria um gesto de cuidado.",
        warning="{name} anda impaciente e quer atencao.",
        sleeping="{name} dorme recolhido no alto do terminal.",
        sick="{name} parece pesado e sem brilho.",
        dead="O abrigo de {name} ficou quieto demais.",
        feed="{name} aceitou a comida e voltou a vigiar em silencio.",
        play="{name} circulou pelo terminal e voltou desperto.",
        sleep="{name} recolheu as asas para descansar.",
        sleep_again="{name} ja esta dormindo. Melhor respeitar o descanso.",
        clean="{name} ajeitou as penas e ficou em boa forma.",
        doctor="{name} recebeu cuidados e voltou a se firmar.",
        doctor_ok="{name} estava bem, mas tolerou a consulta.",
    ),
    "owl": SpeciesFlavor(
        arrival="Aterrissou em silencio e tomou conta do turno da noite.",
        healthy="{name} parece atento, sereno e bem disposto.",
        okay="{name} esta bem, mas quer um pouco mais de atencao.",
        warning="{name} pisca devagar pedindo cuidado.",
        sleeping="{name} cochila tranquilo no seu canto.",
        sick="{name} esta abatido e precisa de ajuda.",
        dead="O galho de {name} ficou vazio.",
        feed="{name} comeu com calma e ficou satisfeito.",
        play="{name} abriu as asas, se moveu um pouco e ficou mais leve.",
        sleep="{name} se acomodou para um descanso profundo.",
        sleep_again="{name} ja esta dormindo. Melhor nao acordar.",
        clean="{name} ajeitou as penas e ficou impecavel.",
        doctor="{name} recebeu cuidados e voltou a respirar melhor.",
        doctor_ok="{name} nao precisava de tratamento, mas aceitou a revisao.",
    ),
    "blob": SpeciesFlavor(
        arrival="Surgiu no terminal e decidiu ficar por aqui.",
        healthy="{name} vibra tranquilo e parece em boa forma.",
        okay="{name} esta razoavel, mas quer um pouco mais de cuidado.",
        warning="{name} oscila sem muita paciencia.",
        sleeping="{name} descansa em silencio no proprio canto.",
        sick="{name} perdeu a forma e precisa de ajuda.",
        dead="O lugar de {name} ficou vazio.",
        feed="{name} absorveu a comida e ficou contente.",
        play="{name} quicou pelo terminal e se divertiu.",
        sleep="{name} se recolheu para descansar.",
        sleep_again="{name} ja esta dormindo. Melhor deixar quieto.",
        clean="{name} recuperou a forma e ficou mais estavel.",
        doctor="{name} recebeu cuidados e se recompôs.",
        doctor_ok="{name} estava bem, mas aprovou o cuidado extra.",
    ),
}


def normalize_species(species: str) -> str:
    candidate = (species or "").strip().lower()
    candidate = SPECIES_ALIASES.get(candidate, candidate)
    return candidate if candidate in SPECIES else SPECIES[0]


def species_flavor(species: str) -> SpeciesFlavor:
    return SPECIES_FLAVOR[normalize_species(species)]


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def create_pet(owner_uid: int, username: str, name: str, species: str, now: datetime) -> Pet:
    species_name = normalize_species(species)
    flavor = species_flavor(species_name)
    return Pet(
        owner_uid=owner_uid,
        username=username,
        name=name,
        species=species_name,
        created_at=now,
        last_interaction_at=now,
        last_update_at=now,
        age_hours=0.0,
        hunger=18.0,
        energy=78.0,
        mood=82.0,
        hygiene=76.0,
        health=92.0,
        is_sleeping=False,
        sleeping_since=None,
        illness=False,
        alive=True,
        cause_of_death=None,
        last_message=flavor.arrival,
    )


def general_status(pet: Pet) -> str:
    if not pet.alive:
        return "morto"
    worst = min(100.0 - pet.hunger, pet.energy, pet.mood, pet.hygiene, pet.health)
    if worst >= 75:
        return "excelente"
    if worst >= 50:
        return "bem"
    if worst >= 25:
        return "atencao"
    return "critico"


def mood_message(pet: Pet) -> str:
    flavor = species_flavor(pet.species)
    if not pet.alive:
        return flavor.dead.format(name=pet.name)
    if pet.illness:
        return flavor.sick.format(name=pet.name)
    if pet.is_sleeping:
        return flavor.sleeping.format(name=pet.name)
    state = general_status(pet)
    if state == "excelente":
        return flavor.healthy.format(name=pet.name)
    if state == "bem":
        return flavor.okay.format(name=pet.name)
    if state == "atencao":
        return flavor.warning.format(name=pet.name)
    return f"{pet.name} precisa de voce com urgencia."


def _health_pressure(pet: Pet) -> Tuple[float, float]:
    pressure = 0.0
    neglect_hours = 0.0
    if pet.hunger >= 75:
        pressure += (pet.hunger - 74) / 26
        neglect_hours += 1.0
    if pet.energy <= 25:
        pressure += (26 - pet.energy) / 26
        neglect_hours += 1.0
    if pet.hygiene <= 25:
        pressure += (26 - pet.hygiene) / 26
        neglect_hours += 1.0
    return pressure, neglect_hours


def apply_time(pet: Pet, now: datetime, tuning: Tuning) -> Pet:
    if now <= pet.last_update_at:
        return pet.evolve(last_message=mood_message(pet))
    elapsed_hours = (now - pet.last_update_at).total_seconds() / 3600.0
    age_hours = pet.age_hours + elapsed_hours

    hunger = pet.hunger
    energy = pet.energy
    hygiene = pet.hygiene
    mood = pet.mood
    health = pet.health
    is_sleeping = pet.is_sleeping
    sleeping_since = pet.sleeping_since

    if pet.is_sleeping:
        hunger += tuning.sleep_hunger_per_hour * elapsed_hours
        energy += tuning.sleep_energy_gain_per_hour * elapsed_hours
        hygiene -= (tuning.hygiene_loss_per_hour * 0.35) * elapsed_hours
        if energy >= 92:
            is_sleeping = False
            sleeping_since = None
    else:
        hunger += tuning.hunger_per_hour * elapsed_hours
        energy -= tuning.energy_loss_per_hour * elapsed_hours
        hygiene -= tuning.hygiene_loss_per_hour * elapsed_hours

    hunger = clamp(hunger, 0.0, tuning.max_stat)
    energy = clamp(energy, 0.0, tuning.max_stat)
    hygiene = clamp(hygiene, 0.0, tuning.max_stat)

    comfort = ((100.0 - hunger) + energy + hygiene) / 3.0
    target_mood = clamp((comfort * 0.75) + (health * 0.25))
    if target_mood >= mood:
        mood += tuning.mood_recovery_per_hour * elapsed_hours
    else:
        mood -= tuning.mood_penalty_per_hour * elapsed_hours
    mood = clamp((mood + target_mood) / 2.0)

    pressure, neglect_markers = _health_pressure(
        pet.evolve(hunger=hunger, energy=energy, hygiene=hygiene, mood=mood, health=health)
    )
    if pressure > 0:
        health -= tuning.health_penalty_per_hour * pressure * elapsed_hours
    else:
        health += tuning.health_recovery_per_hour * elapsed_hours
    health = clamp(health, 0.0, tuning.max_stat)

    illness = pet.illness or health <= tuning.illness_threshold
    if illness and health >= tuning.illness_threshold + 18:
        illness = False

    dead = not pet.alive
    cause = pet.cause_of_death
    neglect_hours = elapsed_hours * neglect_markers
    if health <= 0:
        dead = True
        cause = "Saude zerada apos negligencia prolongada."
    elif neglect_hours >= tuning.death_threshold_hours:
        dead = True
        cause = "Abandono completo por tempo demais."

    if dead:
        return pet.evolve(
            age_hours=age_hours,
            hunger=hunger,
            energy=energy,
            mood=0.0,
            hygiene=hygiene,
            health=0.0,
            is_sleeping=False,
            sleeping_since=None,
            illness=True,
            alive=False,
            cause_of_death=cause,
            last_update_at=now,
            last_message=mood_message(
                pet.evolve(
                    alive=False,
                    cause_of_death=cause,
                    age_hours=age_hours,
                    hunger=hunger,
                    energy=energy,
                    hygiene=hygiene,
                    health=0.0,
                    mood=0.0,
                    is_sleeping=False,
                    sleeping_since=None,
                    illness=True,
                    last_update_at=now,
                )
            ),
        )

    updated = pet.evolve(
        age_hours=age_hours,
        hunger=hunger,
        energy=energy,
        mood=mood,
        hygiene=hygiene,
        health=health,
        is_sleeping=is_sleeping,
        sleeping_since=sleeping_since,
        illness=illness,
        last_update_at=now,
    )
    return updated.evolve(last_message=mood_message(updated))


def interact(pet: Pet, action: str, now: datetime, tuning: Tuning) -> Pet:
    pet = apply_time(pet, now, tuning)
    if not pet.alive:
        return pet

    hunger = pet.hunger
    energy = pet.energy
    hygiene = pet.hygiene
    mood = pet.mood
    health = pet.health
    is_sleeping = pet.is_sleeping
    sleeping_since = pet.sleeping_since
    message = pet.last_message
    flavor = species_flavor(pet.species)

    if action == "feed":
        hunger = clamp(hunger - 28)
        energy = clamp(energy + 6)
        mood = clamp(mood + 8)
        health = clamp(health + 3)
        message = flavor.feed.format(name=pet.name)
    elif action == "play":
        hunger = clamp(hunger + 10)
        energy = clamp(energy - 14)
        hygiene = clamp(hygiene - 7)
        mood = clamp(mood + 16)
        health = clamp(health + 2)
        message = flavor.play.format(name=pet.name)
    elif action == "sleep":
        if pet.is_sleeping:
            message = flavor.sleep_again.format(name=pet.name)
        else:
            is_sleeping = True
            sleeping_since = now
            mood = clamp(mood + 4)
            message = flavor.sleep.format(name=pet.name)
    elif action == "clean":
        hygiene = clamp(hygiene + 32)
        mood = clamp(mood + 6)
        health = clamp(health + 4)
        message = flavor.clean.format(name=pet.name)
    elif action == "doctor":
        if pet.illness or pet.health < 70:
            health = clamp(health + 24)
            mood = clamp(mood + 5)
            energy = clamp(energy + 4)
            message = flavor.doctor.format(name=pet.name)
        else:
            message = flavor.doctor_ok.format(name=pet.name)

    illness = pet.illness
    if health >= tuning.illness_threshold + 15:
        illness = False

    updated = pet.evolve(
        hunger=hunger,
        energy=energy,
        hygiene=hygiene,
        mood=mood,
        health=health,
        is_sleeping=is_sleeping,
        sleeping_since=sleeping_since,
        illness=illness,
        last_interaction_at=now,
        last_update_at=now,
        last_message=message,
    )
    return updated
