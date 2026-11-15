"""
Wakfu Damage Meter - Class Recognition Engine (v1.6.0.40)
========================================================
- GARANTIA DE SEGURANÇA: Leitura 100% passiva de arquivos de texto (.log). Zero injeção de memória.
- Correções da v1.6.0.40:
  1. Restauração do breed 19 para Huppermago e breed 18 para Eliotrope (confirmado via logs/prints reais em jogo).
  2. Proibição de cache em avatares fallback (letra inicial): garante que o quadrado colorido nunca trave o carregamento do retrato real da classe.
  3. Reconhecimento suplementar de classe por feitiços característicos (caso o medidor seja aberto com a luta já em andamento).
  4. Proteção total do Zobal e seus clones mantida da v1.6.0.38/39.
"""

import ctypes
import glob
import json
import os
import re
import sys
import threading
import time
import tkinter as tk
import unicodedata
from collections import defaultdict
from tkinter import filedialog, messagebox
import urllib.request
import zipfile
import shutil

import keyboard
from PIL import Image, ImageDraw, ImageTk, ImageOps

try:
    import openpyxl
    from openpyxl.chart import BarChart, LineChart, Reference
    from openpyxl.styles import Font as CellFont, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.xml.functions import fromstring
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# ============================== CONFIG E CORES ==============================

APP_VERSION = "1.6.0.40"
CONFIG_SCHEMA_VERSION = 4
UPDATE_JSON_URL = "https://raw.githubusercontent.com/nemesis356/wakfu-overlay-updater/refs/heads/main/versao.txt"

DEFAULT_LOG_PATH = os.path.expandvars(r"%APPDATA%\zaap\gamesLogs\wakfu\logs")
POLL_INTERVAL_SECONDS = 0.25
CONFIG_FILENAME = "wakfu_damage_meter_config.json"
HISTORY_FILENAME = "historico_danos.json"
EXCEL_FILENAME = "Wakfu_Historico_De_Danos.xlsx"

MAX_FIGHTS_PER_LEVEL = 30

EXCEL_CHAR_PALETTE = ["2E6BE6", "D9534F", "2E9E5B", "8E44AD", "E67E22", "16A085"]
C_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

BASE_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
AVATAR_DIR = os.path.join(BASE_DIR, "avatares")
os.makedirs(AVATAR_DIR, exist_ok=True)

APP_WIDTH = 475
APP_HEIGHT = 125
DETAILS_HEIGHT = 210

CHROMA_KEY = "#000001"
COLOR_HEADER = "#151515"
COLOR_BODY = "#1c1c1c"
CARD_NORMAL_BG = "#262626"
CARD_NORMAL_OUTLINE = "#1a1a1a"
CARD_MVP_OUTLINE = "#e8c95a"

TAB_ACTIVE_BG = "#2d2d2d"
TAB_ACTIVE_OUTLINE = "#e8c95a"

TEXT_YELLOW = "#e8c95a"
TEXT_GRAY = "#a0a0a0"

# Tabela Oficial de IDs de Raça (AvatarBreed) do motor do Wakfu:
# 15 = Kilorf (Ouginak) | 16 = Steamer | 18 = Eliotrope | 19 = Huppermago
CLASS_MAP = {
    "1": ["Feca", "Féca"],
    "2": ["Osamodas", "Osa"],
    "3": ["Enutrof", "Enu"],
    "4": ["Sram"],
    "5": ["Xelor", "Xélor"],
    "6": ["Ecaflip", "Eca"],
    "7": ["Eniripsa", "Eniripsia", "Eni"],
    "8": ["Iop"],
    "9": ["Cra", "Crâ"],
    "10": ["Sadida", "Sadi"],
    "11": ["Sacrier", "Sacrieur", "Sacri"],
    "12": ["Pandawa", "Panda"],
    "13": ["Ladino", "Roublard", "Rogue"],
    "14": ["Zobal", "Masqueraider", "Zob"],
    "15": ["Kilorf", "Ouginak"],
    "16": ["Steamer", "Foggernaut"],
    "17": ["Eliotrope", "Elio"],
    "18": ["Eliotrope", "Elio"],
    "19": ["Huppermago", "Huppermage", "Hupper", "Hupermago", "Hupermage", "Huper"]
}

ROUBLARD_BOMBS = {
    "Bomba de Fogo", "Bomba de Água", "Bomba de Agua",
    "Bomba Paralisante", "Bomba Cegante", "Megabomba"
}

SRAM_DOUBLES = {
    "Dublê", "Dublê Sram", "Duble", "Duble Sram", "Double", "Double Sram"
}

ZOBAL_CLONES = {
    "Duplo", "Duplo Zobal", "Clone", "Clone Zobal",
    "Espírito Mascarado", "Espirito Mascarado", "Double Zobal"
}

# ============================== REGEX ================================

FL_BREED_RE = re.compile(
    r"\[_FL_\] fightId=(?P<fight_id>\d+) (?P<name>.+?) breed : (?P<breed>\d+)(?:\s*\[[^\]]+\]\s*isControlledByAI=(?P<ai>true|false))?"
)
FL_BYTES_RE = re.compile(rb"[^\r\n]*\[_FL_\] fightId=\d+[^\r\n]*")
PLAYER_LEVEL_RE = re.compile(r"\[Registro de Jogo\]\s*(?P<name>.+?) agora está (?:em seu nível real|no nível ajustado) \d+")
EXP_GAIN_RE = re.compile(r"^(?P<name>.+?):\s*\+[\d.]+\s*pontos de EXP\.")

COMBAT_LINE_RE = re.compile(r"\[Registro de Lutas\]\s*(.*)$")
CAST_RE = re.compile(r"^(?P<caster>.+?) lança (?P<spell>.+?)\.(?P<crit> \(Crítico\))?\s*$")
SUMMON_RE = re.compile(r"^(?P<caster>.+?):\s*Invoca (?:um |uma |o |a )?(?P<summon>.+?)\.?\s*$")
PV_RE = re.compile(r"^(?P<target>.+?):\s*(?P<sign>[+-])(?P<amount>\d[\d.]*)\s*PV\b(?P<tags>.*)$")
ARMOR_RE = re.compile(r"^(?P<target>.+?):\s*(?P<amount>\d[\d.]*)\s*Armadura\b")
FIGHT_END_RE = re.compile(r"(?:O combate terminou|\[FIGHT\] End fight(?:\s+with id\s+(?P<fight_id>\d+))?)")

IGNORED_TAGS = {
    "Água", "Agua", "Ar", "Terra", "Fogo", "Luz", "Trevas", "Sombras", "Neutro",
    "Neutro - Roubo de Vida", "Combo de roubo de vida", "Parada!", "Combo de danos extras",
    "Retorno das Chamas", "Fúria Sanguinária", "Punição", "Castigo", "Estilhaçador",
    "Primeiro Ricochete", "Segundo Ricochete", "Fúria", "Perdido", "Entalhe"
}
TURN_END_RE = re.compile(r"segundos? adiados? para o turno seguinte\.")
STATUS_APPLY_RE = re.compile(r"^(?P<target>.+?):\s*(?P<effect>[^(]+?)\s*\([^)]*(?:Nv\.|Nív\.)[^)]*\).*$")
GLYPH_RE = re.compile(r"^.+?:\s*Coloca (?:o |a )?(?:[Gg]lifo|[Aa]rmadilha|[Mm]arca|[Ss]ímbolo) (?P<effect>.+?)\.?\s*$")

SELF_OWNED_EFFECTS = {"Flamejante"}
STICKY_OWNER_EFFECTS = {"Tetatoxina"}
BLOCK_RE = re.compile(r"^(?P<who>.+?):\s*[\d.]+\s*Bloqueio\b")

# ============================== LÓGICA CORE =================================

class FightState:
    def __init__(self, whitelist_getter=None, on_class_discovered=None):
        self.lock = threading.Lock()
        self.whitelist_getter = whitelist_getter or (lambda: set())
        self.on_class_discovered = on_class_discovered
        self.version = 0
        self.character_class = {}
        self.is_ai_controlled = {}
        self.last_fight_data = None
        self.on_fight_end_callback = None
        self.on_fight_start_callback = None
        self.reset(is_initial=True)

    def load_persisted_classes(self, classes_dict, ai_dict):
        with self.lock:
            if isinstance(classes_dict, dict):
                for k, v in classes_dict.items():
                    if str(v) in CLASS_MAP:
                        self.character_class[k] = str(v)
            if isinstance(ai_dict, dict):
                for k, v in ai_dict.items():
                    if v is False:
                        self.is_ai_controlled[k] = False

    def reset(self, is_initial=False):
        with self.lock:
            if not is_initial and (getattr(self, 'characters', set()) or getattr(self, 'current_combatants', set())):
                has_any_action = any(
                    bool(d) for d in (self.damage, self.received, self.healing, self.armor)
                )
                if has_any_action:
                    self.last_fight_data = {
                        "damage": {c: dict(t) for c, t in self.damage.items()},
                        "received": {c: dict(t) for c, t in self.received.items()},
                        "healing": {c: dict(t) for c, t in self.healing.items()},
                        "armor": {c: dict(t) for c, t in self.armor.items()},
                        "characters": set(self.characters),
                        "current_combatants": set(self.current_combatants),
                        "character_class": dict(self.character_class),
                        "is_ai_controlled": dict(self.is_ai_controlled),
                        "summon_owner": dict(self.summon_owner)
                    }

            self.version += 1
            self.current_fight_id = None
            self.character_turn = defaultdict(lambda: 1)
            self.awaiting_new_turn_for = defaultdict(bool)
            self.current_caster = None
            self.active_turn_owner = None
            self.active_raw_caster = None
            self.last_cast_spell = None
            self.last_damaged_ally = None
            self.combat_phase_started = False
            self.fight_ended = False

            self.damage = defaultdict(lambda: defaultdict(int))
            self.received = defaultdict(lambda: defaultdict(int))
            self.healing = defaultdict(lambda: defaultdict(int))
            self.armor = defaultdict(lambda: defaultdict(int))

            self.characters = set()
            self.current_combatants = set()
            self.enemy_entities = set()
            self.summon_owner = {}
            self.tag_owner = {}
            self.self_owned_carriers = defaultdict(list)
            self.active_aoe_effect = {}
            self.last_blocker = None
            self.last_damaged = None
            self.last_update_ts = None
            self.is_combat_active = False

    def _is_player_entity(self, name: str) -> bool:
        if name in ROUBLARD_BOMBS or name in SRAM_DOUBLES or name in ZOBAL_CLONES:
            return False
        if name in self.whitelist_getter():
            return True
        if name in self.current_combatants:
            return True
        if name in self.summon_owner:
            return False
        if self.is_ai_controlled.get(name) is False:
            return True
        if self.is_ai_controlled.get(name) is True:
            return False
        return self.character_class.get(name) in CLASS_MAP

    def _find_class_owner(self, target_breed: str):
        for name in (self.current_combatants | self.characters):
            if self.character_class.get(name) == target_breed and self._is_player_entity(name):
                return name
        for name, breed in self.character_class.items():
            if breed == target_breed and self._is_player_entity(name):
                return name
        return None

    def _resolve_caster_owner(self, name: str) -> str:
        if not name:
            return name
        if name in self.current_combatants or name in self.whitelist_getter():
            return name
        if name in self.summon_owner:
            return self.summon_owner[name]
        if name in ROUBLARD_BOMBS:
            roub = self._find_class_owner("13")
            if roub:
                self.summon_owner[name] = roub
                self.enemy_entities.discard(name)
                return roub
        if name in SRAM_DOUBLES:
            sram = self._find_class_owner("4")
            if sram:
                self.summon_owner[name] = sram
                self.enemy_entities.discard(name)
                return sram
        if name in ZOBAL_CLONES:
            zob = self._find_class_owner("14")
            if zob:
                self.summon_owner[name] = zob
                self.enemy_entities.discard(name)
                return zob
        if not self._is_player_entity(name):
            tag_own = self.tag_owner.get(name)
            if tag_own and self._is_player_entity(tag_own) and tag_own != name:
                self.summon_owner[name] = tag_own
                self.enemy_entities.discard(name)
                return tag_own
        return name

    def _safe_assign_tag(self, effect_name: str, owner_name: str):
        if effect_name in self.current_combatants or effect_name in self.whitelist_getter():
            if effect_name != owner_name:
                return
        is_new_owner_player = self._is_player_entity(owner_name)
        if is_new_owner_player:
            self.tag_owner[effect_name] = owner_name
        else:
            current_owner = self.tag_owner.get(effect_name)
            if not current_owner or not self._is_player_entity(current_owner):
                self.tag_owner[effect_name] = owner_name

    def snapshot(self):
        with self.lock:
            return {
                "version": self.version,
                "damage": {c: dict(t) for c, t in self.damage.items()},
                "received": {c: dict(t) for c, t in self.received.items()},
                "healing": {c: dict(t) for c, t in self.healing.items()},
                "armor": {c: dict(t) for c, t in self.armor.items()},
                "characters": set(self.characters),
                "current_combatants": set(self.current_combatants),
                "character_class": dict(self.character_class),
                "is_ai_controlled": dict(self.is_ai_controlled),
                "summon_owner": dict(self.summon_owner),
                "last_fight_data": self.last_fight_data,
                "last_update_ts": self.last_update_ts,
                "is_combat_active": self.is_combat_active
            }

    def register_fl_line(self, raw_line: str):
        breed_m = FL_BREED_RE.search(raw_line)
        if breed_m:
            name = breed_m.group("name").strip()
            breed = breed_m.group("breed").strip()
            ai_str = breed_m.group("ai")
            if breed not in CLASS_MAP or name in ROUBLARD_BOMBS or name in SRAM_DOUBLES or name in ZOBAL_CLONES:
                return
            if ai_str == "true":
                with self.lock:
                    if breed in ("4", "14"):
                        if self.character_class.get(name) != breed:
                            self.character_class[name] = breed
                        return
                    if (
                        self.is_ai_controlled.get(name) is not False
                        and name not in self.current_combatants
                        and name not in self.characters
                    ):
                        self.is_ai_controlled[name] = True
                return
            changed = False
            with self.lock:
                if self.character_class.get(name) != breed:
                    self.character_class[name] = breed
                    changed = True
                if ai_str == "false" and self.is_ai_controlled.get(name) is not False:
                    self.is_ai_controlled[name] = False
                    changed = True
            if changed and self.on_class_discovered:
                self.on_class_discovered()

    def prescan_lines(self, lines):
        self.reset(is_initial=True)
        start_indices = []

        for idx, raw_line in enumerate(lines):
            if "[_FL_]" in raw_line:
                self.register_fl_line(raw_line)
            elif "CREATION DU COMBAT" in raw_line:
                start_indices.append(idx)
            elif "[Registro de Jogo]" in raw_line:
                lvl_m = PLAYER_LEVEL_RE.search(raw_line)
                if lvl_m:
                    p_name = lvl_m.group("name").strip()
                    with self.lock:
                        self.is_ai_controlled[p_name] = False

        if start_indices:
            start_from = start_indices[-2] if len(start_indices) >= 2 else start_indices[-1]
            for raw_line in lines[start_from:]:
                self.process_line(raw_line, suppress_callbacks=True)
        elif lines:
            for raw_line in lines:
                self.process_line(raw_line, suppress_callbacks=True)

        if not self.is_combat_active:
            self.reset(is_initial=False)

    def process_line(self, raw_line: str, suppress_callbacks: bool = False):
        if "[Registro de Jogo]" in raw_line:
            lvl_m = PLAYER_LEVEL_RE.search(raw_line)
            if lvl_m:
                p_name = lvl_m.group("name").strip()
                changed = False
                with self.lock:
                    if self.is_ai_controlled.get(p_name) is not False:
                        self.is_ai_controlled[p_name] = False
                        changed = True
                if changed and not suppress_callbacks and self.on_class_discovered:
                    self.on_class_discovered()
            return

        if "CREATION DU COMBAT" in raw_line:
            self.reset()
            with self.lock:
                self.is_combat_active = True
                self.fight_ended = False
                self.last_update_ts = time.time()
                self.version += 1
            if not suppress_callbacks and self.on_fight_start_callback:
                self.on_fight_start_callback()
            return

        if "[_FL_]" in raw_line:
            breed_m = FL_BREED_RE.search(raw_line)
            if breed_m:
                name = breed_m.group("name").strip()
                breed = breed_m.group("breed").strip()
                ai_str = breed_m.group("ai")
                fight_id = breed_m.group("fight_id")
                is_ai = (ai_str == "true") if ai_str is not None else None

                changed = False
                with self.lock:
                    if name in ROUBLARD_BOMBS:
                        roub = self._find_class_owner("13")
                        if roub:
                            self.summon_owner[name] = roub
                            self.enemy_entities.discard(name)
                            self._safe_assign_tag(name, roub)
                        return

                    if name in SRAM_DOUBLES:
                        sram = self._find_class_owner("4")
                        if sram:
                            self.summon_owner[name] = sram
                            self.enemy_entities.discard(name)
                            self._safe_assign_tag(name, sram)
                        return

                    if name in ZOBAL_CLONES:
                        zob = self._find_class_owner("14")
                        if zob:
                            self.summon_owner[name] = zob
                            self.enemy_entities.discard(name)
                            self._safe_assign_tag(name, zob)
                        return

                    is_known_human = (
                        name in self.current_combatants
                        or name in self.whitelist_getter()
                        or self.is_ai_controlled.get(name) is False
                        or (name in self.characters and breed in CLASS_MAP and name not in self.enemy_entities)
                        or (name == self.current_caster and breed in CLASS_MAP)
                    )
                    if is_known_human:
                        if breed in CLASS_MAP and self.character_class.get(name) != breed:
                            self.character_class[name] = breed
                            changed = True
                        self.summon_owner.pop(name, None)
                        self.enemy_entities.discard(name)
                        self.is_ai_controlled[name] = False
                        if not self.fight_ended:
                            self.current_combatants.add(name)
                            self.is_combat_active = True
                        self.version += 1
                        if changed and not suppress_callbacks and self.on_class_discovered:
                            self.on_class_discovered()
                        return

                    if (
                        self.combat_phase_started
                        and name not in self.current_combatants
                        and name not in self.whitelist_getter()
                        and self.current_caster
                        and self._is_player_entity(self.current_caster)
                        and name != self.current_caster
                    ):
                        if is_ai is True or breed == self.character_class.get(self.current_caster) or breed not in CLASS_MAP:
                            self.summon_owner[name] = self.current_caster
                            self.enemy_entities.discard(name)
                            self._safe_assign_tag(name, self.current_caster)
                            return

                    if breed in CLASS_MAP and is_ai is not True and name not in self.summon_owner:
                        if self.character_class.get(name) != breed:
                            self.character_class[name] = breed
                            changed = True
                        if is_ai is False and self.is_ai_controlled.get(name) is not False:
                            self.is_ai_controlled[name] = False
                            changed = True

                    if self.fight_ended:
                        if changed and not suppress_callbacks and self.on_class_discovered:
                            self.on_class_discovered()
                        return

                    if self.current_fight_id and fight_id and fight_id != self.current_fight_id:
                        if changed and not suppress_callbacks and self.on_class_discovered:
                            self.on_class_discovered()
                        return

                    is_ally_candidate = (
                        name in self.whitelist_getter()
                        or is_ai is False
                        or (is_ai is None and breed in CLASS_MAP)
                    )

                    if is_ai is True:
                        if name not in self.summon_owner and name not in self.current_combatants:
                            self.enemy_entities.add(name)
                            if self.is_ai_controlled.get(name) is not False:
                                self.is_ai_controlled[name] = True
                    else:
                        if name not in self.summon_owner:
                            if self.character_class.get(name) != breed and breed in CLASS_MAP:
                                self.character_class[name] = breed
                                changed = True
                            if is_ai is False and self.is_ai_controlled.get(name) is not False:
                                self.is_ai_controlled[name] = False
                                if breed in CLASS_MAP:
                                    changed = True
                            if is_ally_candidate:
                                self.current_combatants.add(name)
                                if fight_id and self.current_fight_id is None:
                                    self.current_fight_id = fight_id
                                self.is_combat_active = True
                    self.version += 1
                if changed and not suppress_callbacks and self.on_class_discovered:
                    self.on_class_discovered()
            return

        end_m = FIGHT_END_RE.search(raw_line)
        if end_m:
            ended_id = end_m.group("fight_id")
            with self.lock:
                if ended_id and self.current_fight_id and ended_id != self.current_fight_id:
                    return
                if not self.fight_ended:
                    self.fight_ended = True
                    if self.is_combat_active:
                        self.is_combat_active = False
                        if not suppress_callbacks and self.on_fight_end_callback:
                            end_snap = {
                                "damage": {c: dict(t) for c, t in self.damage.items()},
                                "characters": set(self.characters),
                                "current_combatants": set(self.current_combatants),
                                "character_class": dict(self.character_class),
                                "is_ai_controlled": dict(self.is_ai_controlled),
                                "summon_owner": dict(self.summon_owner)
                            }
                            self.on_fight_end_callback(end_snap)
            return

        m = COMBAT_LINE_RE.search(raw_line)
        if not m: return
        content = m.group(1).strip()
        if not content: return

        exp_m = EXP_GAIN_RE.match(content)
        if exp_m:
            p_name = exp_m.group("name").strip()
            changed = False
            with self.lock:
                if p_name not in self.summon_owner and self.is_ai_controlled.get(p_name) is not False:
                    self.is_ai_controlled[p_name] = False
                    self.characters.add(p_name)
                    self.version += 1
                    changed = True
            if changed and not suppress_callbacks and self.on_class_discovered:
                self.on_class_discovered()
            return

        with self.lock:
            if self.fight_ended:
                return

            summon_m = SUMMON_RE.match(content)
            if summon_m:
                self.is_combat_active = True
                owner = summon_m.group("caster").strip()
                summon = summon_m.group("summon").strip()
                resolved_owner = self._resolve_caster_owner(owner)

                if (
                    summon == resolved_owner
                    or summon in self.current_combatants
                    or summon in self.whitelist_getter()
                    or self.is_ai_controlled.get(summon) is False
                ):
                    self.summon_owner.pop(summon, None)
                    self.enemy_entities.discard(summon)
                    if self._is_player_entity(resolved_owner):
                        self.current_combatants.add(resolved_owner)
                        self.characters.add(resolved_owner)
                    self.version += 1
                    return

                if self._is_player_entity(resolved_owner) and summon != resolved_owner:
                    self.summon_owner[summon] = resolved_owner
                    self.enemy_entities.discard(summon)
                    self.current_combatants.discard(summon)
                    self.characters.discard(summon)
                    if summon not in self.whitelist_getter() and self.character_class.get(summon) not in CLASS_MAP:
                        self.is_ai_controlled.pop(summon, None)
                        self.character_class.pop(summon, None)
                    self._safe_assign_tag(summon, resolved_owner)
                    self.version += 1
                elif not self._is_player_entity(resolved_owner):
                    self.enemy_entities.add(summon)
                return

            pv_m = PV_RE.match(content)
            if pv_m:
                self.is_combat_active = True
                amount = int(pv_m.group("amount").replace(".", ""))
                if amount == 0:
                    return
                sign = pv_m.group("sign")
                target = pv_m.group("target").strip()

                is_pure_ally_summon = (
                    (target in self.summon_owner or target in ROUBLARD_BOMBS or target in SRAM_DOUBLES or target in ZOBAL_CLONES)
                    and target not in self.enemy_entities
                )
                is_ally_target = (self._is_player_entity(target) or is_pure_ally_summon)

                if sign == "-":
                    if self._is_player_entity(target):
                        self.last_damaged_ally = target
                    if (
                        target not in self.summon_owner
                        and target not in ROUBLARD_BOMBS
                        and target not in SRAM_DOUBLES
                        and target not in ZOBAL_CLONES
                        and target not in self.enemy_entities
                    ):
                        self.received[target][self.character_turn[target]] += amount
                        self.characters.add(target)

                tag_list = re.findall(r"\(([^)]+)\)", pv_m.group("tags"))
                special_tags = [t for t in tag_list if t not in IGNORED_TAGS]
                caster = self.current_caster

                if special_tags:
                    for tag_name in reversed(special_tags):
                        if tag_name in ROUBLARD_BOMBS:
                            roub = self._find_class_owner("13")
                            if roub:
                                caster = roub
                                break
                        if tag_name in SRAM_DOUBLES:
                            sram = self._find_class_owner("4")
                            if sram:
                                caster = sram
                                break
                        if tag_name in ZOBAL_CLONES:
                            zob = self._find_class_owner("14")
                            if zob:
                                caster = zob
                                break
                        if tag_name == "Contra-Ataque" and (self.last_damaged or self.last_blocker):
                            caster = self.last_damaged or self.last_blocker
                            break
                        elif tag_name in SELF_OWNED_EFFECTS:
                            if tag_name in self.active_aoe_effect:
                                caster = self.active_aoe_effect[tag_name]
                            else:
                                carriers = self.self_owned_carriers.get(tag_name)
                                caster = (
                                    carriers.pop(0) if carriers
                                    else (self.current_caster or self.tag_owner.get(tag_name))
                                )
                                if caster:
                                    self.active_aoe_effect[tag_name] = caster
                            break
                        elif tag_name in self.tag_owner:
                            caster = self.tag_owner[tag_name]
                            break
                        elif tag_name in STICKY_OWNER_EFFECTS:
                            if self.current_caster:
                                self._safe_assign_tag(tag_name, self.current_caster)
                            break

                if caster:
                    caster = self._resolve_caster_owner(caster)
                    if caster not in self.enemy_entities:
                        self.characters.add(caster)
                    turn_to_log = self.character_turn[caster]
                    self.last_update_ts = time.time()

                    is_ally_caster = self._is_player_entity(caster)

                    if sign == "-":
                        if caster != target:
                            if not (is_ally_caster and is_ally_target):
                                self.damage[caster][turn_to_log] += amount
                                self.last_damaged = target
                    else:
                        if is_ally_target:
                            self.healing[caster][turn_to_log] += amount

                    self.version += 1
                return

            armor_m = ARMOR_RE.match(content)
            if armor_m:
                self.is_combat_active = True
                amount = int(armor_m.group("amount").replace(".", ""))
                if amount == 0:
                    return
                target = armor_m.group("target").strip()
                is_pure_ally_summon = (
                    (target in self.summon_owner or target in ROUBLARD_BOMBS or target in SRAM_DOUBLES or target in ZOBAL_CLONES)
                    and target not in self.enemy_entities
                )
                is_ally_target = (self._is_player_entity(target) or is_pure_ally_summon)
                if not is_ally_target:
                    return

                if self.current_caster and self._is_player_entity(self.current_caster) and target != self.last_damaged_ally:
                    caster = self.current_caster
                else:
                    caster = self._resolve_caster_owner(target)

                if self._is_player_entity(caster):
                    self.characters.add(caster)
                    self.armor[caster][self.character_turn[caster]] += amount
                    self.last_update_ts = time.time()
                    self.version += 1
                return

            status_m = STATUS_APPLY_RE.match(content)
            if status_m:
                self.is_combat_active = True
                self.active_aoe_effect.clear()
                target_name = status_m.group("target").strip()
                effect = status_m.group("effect").strip()

                if effect in ROUBLARD_BOMBS or target_name in ROUBLARD_BOMBS:
                    roub = self._find_class_owner("13")
                    if roub:
                        if target_name in ROUBLARD_BOMBS:
                            self.summon_owner[target_name] = roub
                            self.enemy_entities.discard(target_name)
                            self.current_caster = roub
                        self._safe_assign_tag(effect, roub)
                    return

                if effect in SRAM_DOUBLES or target_name in SRAM_DOUBLES:
                    sram = self._find_class_owner("4")
                    if sram:
                        if target_name in SRAM_DOUBLES:
                            self.summon_owner[target_name] = sram
                            self.enemy_entities.discard(target_name)
                            self.current_caster = sram
                        self._safe_assign_tag(effect, sram)
                    return

                if effect in ZOBAL_CLONES or target_name in ZOBAL_CLONES:
                    zob = self._find_class_owner("14")
                    if zob:
                        if target_name in ZOBAL_CLONES:
                            self.summon_owner[target_name] = zob
                            self.enemy_entities.discard(target_name)
                            self.current_caster = zob
                        self._safe_assign_tag(effect, zob)
                    return

                target_ally_owner = self.summon_owner.get(target_name) or (
                    target_name if self._is_player_entity(target_name) else None
                )
                if target_ally_owner and target_name == self.last_damaged_ally:
                    base_caster = target_ally_owner
                elif self.current_caster and self._is_player_entity(self.current_caster):
                    base_caster = self.current_caster
                elif target_ally_owner:
                    base_caster = target_ally_owner
                else:
                    base_caster = self.current_caster

                if base_caster:
                    owner_caster = self._resolve_caster_owner(base_caster)
                    if effect in SELF_OWNED_EFFECTS:
                        resolved_target = self._resolve_caster_owner(target_name)
                        carriers = self.self_owned_carriers[effect]
                        if resolved_target in carriers: carriers.remove(resolved_target)
                        carriers.append(resolved_target)
                        self._safe_assign_tag(effect, resolved_target)
                    else:
                        self._safe_assign_tag(effect, owner_caster)
                return

            cast_m = CAST_RE.match(content)
            if cast_m:
                self.is_combat_active = True
                self.combat_phase_started = True
                self.active_aoe_effect.clear()
                self.last_damaged_ally = None
                raw_caster = cast_m.group("caster").strip()
                caster = self._resolve_caster_owner(raw_caster)
                spell = cast_m.group("spell").strip()
                self.last_cast_spell = spell
                self.active_raw_caster = raw_caster

                if raw_caster == caster:
                    if self.active_turn_owner and self.active_turn_owner != caster:
                        self.awaiting_new_turn_for[self.active_turn_owner] = True
                    self.active_turn_owner = caster
                    if self.awaiting_new_turn_for[caster]:
                        self.character_turn[caster] += 1
                        self.awaiting_new_turn_for[caster] = False
                elif raw_caster not in SRAM_DOUBLES and raw_caster not in ZOBAL_CLONES:
                    if self.active_turn_owner:
                        self.awaiting_new_turn_for[self.active_turn_owner] = True
                        self.active_turn_owner = None

                self.current_caster = caster
                if caster not in self.enemy_entities:
                    self.characters.add(caster)
                    if self._is_player_entity(caster):
                        self.current_combatants.add(caster)
                self._safe_assign_tag(spell, caster)
                self.version += 1
                return

            if TURN_END_RE.search(content):
                self.combat_phase_started = True
                self.active_aoe_effect.clear()
                self.last_damaged_ally = None
                if self.active_turn_owner:
                    if (
                        (self.active_raw_caster in SRAM_DOUBLES and self.character_class.get(self.active_turn_owner) == "4")
                        or (self.active_raw_caster in ZOBAL_CLONES and self.character_class.get(self.active_turn_owner) == "14")
                    ):
                        self.active_raw_caster = self.active_turn_owner
                        self.current_caster = self.active_turn_owner
                        self.last_cast_spell = None
                        self.version += 1
                        return
                    self.awaiting_new_turn_for[self.active_turn_owner] = True
                self.current_caster = None
                self.active_turn_owner = None
                self.active_raw_caster = None
                self.last_cast_spell = None
                self.version += 1
                return

            block_m = BLOCK_RE.match(content)
            if block_m:
                self.last_blocker = block_m.group("who").strip()
                return

            glyph_m = GLYPH_RE.match(content)
            if glyph_m and self.current_caster:
                effect = glyph_m.group("effect").strip()
                owner_caster = self._resolve_caster_owner(self.current_caster)
                self._safe_assign_tag(effect, owner_caster)
                return

# ============================== THREADS =================================

class CustomHotkeyManager:
    def __init__(self, callback):
        self.callback = callback
        self.current_hotkey = None

    def update_hotkey(self, new_hotkey):
        if self.current_hotkey:
            try: keyboard.remove_hotkey(self.current_hotkey)
            except Exception: pass

        self.current_hotkey = new_hotkey
        if self.current_hotkey:
            try: keyboard.add_hotkey(self.current_hotkey, self.callback, suppress=False)
            except Exception: pass

class LogTailer(threading.Thread):
    def __init__(self, state: FightState, path_getter):
        super().__init__(daemon=True)
        self.state = state
        self.path_getter = path_getter
        self._stop_flag = threading.Event()
        self._file_obj = None
        self._current_file_path = None
        self._is_first_open = True
        self._reparse_requested = threading.Event()

    def stop(self): self._stop_flag.set()
    def request_reparse(self): self._reparse_requested.set()

    def _resolve_log_file(self, path: str):
        if not path: return None
        if os.path.isfile(path):
            if os.path.basename(path).lower().startswith(("wakfu_chat", "wakfu_animation")):
                sibling_main = os.path.join(os.path.dirname(path), "wakfu.log")
                if os.path.isfile(sibling_main):
                    return sibling_main
            return path
        if os.path.isdir(path):
            main_log = os.path.join(path, "wakfu.log")
            if os.path.isfile(main_log):
                return main_log
            candidates = [
                f for f in glob.glob(os.path.join(path, "*.log"))
                if not os.path.basename(f).lower().startswith(("wakfu_chat", "wakfu_animation"))
            ]
            return max(candidates, key=os.path.getmtime) if candidates else None
        return None

    def _fast_binary_fl_scan(self, filepath: str, max_offset: int = None):
        try:
            with open(filepath, "rb") as bf:
                chunk_size = 1048576
                overlap = b""
                bytes_read = 0
                while True:
                    if max_offset is not None and bytes_read >= max_offset:
                        break
                    to_read = chunk_size if max_offset is None else min(chunk_size, max_offset - bytes_read)
                    chunk = bf.read(to_read)
                    if not chunk:
                        break
                    bytes_read += len(chunk)
                    data = overlap + chunk
                    last_nl = data.rfind(b"\n")
                    if last_nl != -1:
                        searchable = data[:last_nl]
                        overlap = data[last_nl + 1:]
                    else:
                        searchable = data
                        overlap = b""
                    if b"[_FL_]" in searchable:
                        for match in FL_BYTES_RE.finditer(searchable):
                            line_str = match.group(0).decode("utf-8", errors="replace")
                            self.state.register_fl_line(line_str)
        except Exception:
            pass

    def _scan_backup_logs_for_classes(self, target_file: str):
        log_dir = os.path.dirname(target_file)
        if not os.path.isdir(log_dir):
            return []
        rotated = [
            f for f in glob.glob(os.path.join(log_dir, "wakfu*.log"))
            if os.path.abspath(f) != os.path.abspath(target_file)
            and not os.path.basename(f).lower().startswith(("wakfu_chat", "wakfu_animation"))
        ]
        rotated.sort(key=os.path.getmtime)
        prev_tail_lines = []
        for r_file in rotated[-5:]:
            self._fast_binary_fl_scan(r_file)
        if rotated:
            newest_backup = rotated[-1]
            try:
                with open(newest_backup, "rb") as bf:
                    bf.seek(0, 2)
                    bsize = bf.tell()
                    boff = max(0, bsize - 524288)
                    bf.seek(boff)
                    if boff > 0:
                        bf.readline()
                    prev_tail_lines = bf.read().decode("utf-8", errors="replace").splitlines(True)
            except Exception:
                pass
        return prev_tail_lines

    def run(self):
        while not self._stop_flag.is_set():
            try:
                configured_path = self.path_getter()
                if self._reparse_requested.is_set():
                    if self._file_obj: self._file_obj.close()
                    self._file_obj = None
                    self._current_file_path = None
                    self._is_first_open = True
                    self._reparse_requested.clear()

                if self._file_obj is None:
                    target_file = self._resolve_log_file(configured_path)
                    if target_file is None or not os.path.exists(target_file):
                        time.sleep(POLL_INTERVAL_SECONDS)
                        continue

                    try:
                        self._file_obj = open(target_file, "r", encoding="utf-8", errors="replace")
                    except PermissionError:
                        time.sleep(POLL_INTERVAL_SECONDS)
                        continue

                    self._current_file_path = target_file

                    if self._is_first_open:
                        self._is_first_open = False
                        prev_lines = self._scan_backup_logs_for_classes(target_file)

                        try:
                            file_size = os.path.getsize(target_file)
                        except OSError:
                            file_size = 0

                        scan_window = 2097152
                        scan_offset = max(0, file_size - scan_window)

                        if scan_offset > 0:
                            self._fast_binary_fl_scan(target_file, max_offset=scan_offset)
                            self._file_obj.seek(scan_offset)
                            self._file_obj.readline()
                            recent_lines = self._file_obj.readlines()
                        else:
                            self._file_obj.seek(0)
                            recent_lines = prev_lines + self._file_obj.readlines()

                        self.state.prescan_lines(recent_lines)
                    else:
                        self._file_obj.seek(0)

                try:
                    lines = self._file_obj.readlines()
                    for line in lines:
                        self.state.process_line(line)

                    if self._current_file_path:
                        if not os.path.exists(self._current_file_path):
                            self._file_obj.close()
                            self._file_obj = None
                            continue

                        if os.path.getsize(self._current_file_path) < self._file_obj.tell():
                            self._file_obj.close()
                            self._file_obj = None
                            continue
                except PermissionError:
                    pass
                except Exception:
                    if self._file_obj: self._file_obj.close()
                    self._file_obj = None

                time.sleep(POLL_INTERVAL_SECONDS)
            except Exception:
                time.sleep(POLL_INTERVAL_SECONDS)

# ============================== APLICAÇÃO PRINCIPAL ==============================

class OverlayApp:
    def __init__(self):
        self.app_x = 200
        self.app_y = 50

        self.root = tk.Tk()
        self.root.title(f"Wakfu Damage Meter v{APP_VERSION}")
        self.root.overrideredirect(True)
        self.root.config(bg=CHROMA_KEY)
        self.root.attributes("-transparentcolor", CHROMA_KEY)
        self.root.attributes("-topmost", True)

        self.bg_window = tk.Toplevel(self.root)
        self.bg_window.overrideredirect(True)
        self.bg_window.config(bg=COLOR_BODY)
        self.bg_window.attributes("-topmost", True)

        self.details_root = tk.Toplevel(self.root)
        self.details_root.overrideredirect(True)
        self.details_root.config(bg=CHROMA_KEY)
        self.details_root.attributes("-transparentcolor", CHROMA_KEY)
        self.details_root.attributes("-topmost", True)

        self.details_bg = tk.Toplevel(self.root)
        self.details_bg.overrideredirect(True)
        self.details_bg.config(bg=COLOR_BODY)
        self.details_bg.attributes("-topmost", True)

        icon_path = self._resource_path("icone.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
                self.bg_window.iconbitmap(icon_path)
                self.details_root.iconbitmap(icon_path)
                self.details_bg.iconbitmap(icon_path)
            except Exception: pass

        self.settings_window = None
        self.level_dialog_window = None
        self._modal_dialog_open = False

        self.show_details = False
        self._sync_windows(self.app_x, self.app_y)

        self.roster = set()
        self.included_chars = set()
        self.last_entered_level = ""

        self.pending_fight_queue = []
        self.pending_fight_start = False
        self.pending_clickthrough_toggle = False
        self.pending_config_save = False

        self.state = FightState(
            whitelist_getter=lambda: self.included_chars,
            on_class_discovered=self._request_config_save
        )
        self.state.on_fight_end_callback = self._trigger_level_prompt
        self.state.on_fight_start_callback = self._trigger_fight_start

        self._history_lock = threading.Lock()
        self.combat_history = defaultdict(list)
        self._load_history_db()

        self._last_state_hash = None
        self.clickthrough = False

        self.view_last_fight = False
        self.selected_char = None
        self.details_scroll_y = 0
        self.max_scroll = 0

        self.details_bg.withdraw()
        self.details_root.withdraw()

        self.log_path_var = tk.StringVar(value=DEFAULT_LOG_PATH)
        self.mode_var = tk.StringVar(value="Causado")
        self.opacity_var = tk.IntVar(value=10)
        self.hotkey_var = tk.StringVar(value="ctrl+f12")

        self._avatar_cache = {}
        self._active_card_avatars = []

        self._load_config()
        self._apply_opacity()

        self.img_header_bg = self._create_rounded_bg(APP_WIDTH, 34, 10, fill=COLOR_HEADER, outline=COLOR_HEADER, width=1)
        self.img_pill_active = self._create_rounded_bg(74, 26, 13, fill=TAB_ACTIVE_BG, outline=TAB_ACTIVE_OUTLINE, width=1)
        self.img_card_normal = self._create_rounded_bg(60, 76, 6, fill=CARD_NORMAL_BG, outline=CARD_NORMAL_OUTLINE, width=1)
        self.img_card_mvp = self._create_rounded_bg(60, 76, 6, fill=CARD_NORMAL_BG, outline=CARD_MVP_OUTLINE, width=2)
        self.img_details_bg = self._create_rounded_bg(APP_WIDTH, DETAILS_HEIGHT, 10, fill=COLOR_HEADER, outline=CARD_NORMAL_OUTLINE, width=1)

        self._build_unified_ui()
        self._start_drag_bindings()

        self.hotkey_manager = CustomHotkeyManager(callback=self._request_clickthrough_toggle)
        self.hotkey_manager.update_hotkey(self.hotkey_var.get())

        self.tailer = LogTailer(self.state, lambda: self.log_path_var.get())
        self.tailer.start()

        self.root.after(100, self._apply_window_region)
        self.root.after(200, self._refresh_loop)

        threading.Thread(target=self._check_for_updates, daemon=True).start()

    def _request_clickthrough_toggle(self):
        self.pending_clickthrough_toggle = True

    def _request_config_save(self):
        self.pending_config_save = True

    def _trigger_fight_start(self):
        self.pending_fight_start = True

    # ============================== HISTÓRICO E AGREGAÇÃO EXCEL (MÁX 30 LUTAS) ==============================

    def _normalize_level_key(self, raw_lvl: str) -> str:
        cleaned = re.sub(r'^[Nn][íi]vel\s*', '', str(raw_lvl).strip())
        cleaned = re.sub(r'[\\/*?:\[\]]', '-', cleaned).strip()
        return cleaned or "Geral"

    def _parse_timestamp_sort_key(self, ts_str: str):
        try:
            return (0, time.mktime(time.strptime(str(ts_str).strip(), "%d/%m/%Y %H:%M:%S")))
        except Exception:
            return (1, str(ts_str))

    def _trim_level_history(self, norm_lvl: str):
        if len(self.combat_history[norm_lvl]) > MAX_FIGHTS_PER_LEVEL:
            self.combat_history[norm_lvl] = self.combat_history[norm_lvl][-MAX_FIGHTS_PER_LEVEL:]

    def _add_or_merge_fight_record(self, lvl_key: str, timestamp_str: str, damage_dict: dict, trim: bool = True):
        if not timestamp_str or not isinstance(damage_dict, dict):
            return False
        clean_dmg = {}
        for k, v in damage_dict.items():
            try:
                val = int(float(v))
                if val >= 0:
                    clean_dmg[str(k).strip()] = val
            except (ValueError, TypeError):
                pass
        if not clean_dmg or max(clean_dmg.values(), default=0) == 0:
            return False

        norm_lvl = self._normalize_level_key(lvl_key)
        ts_clean = str(timestamp_str).strip()
        for existing in self.combat_history[norm_lvl]:
            if existing.get("timestamp") == ts_clean:
                changed = False
                for ch, val in clean_dmg.items():
                    if val > existing["damage"].get(ch, 0):
                        existing["damage"][ch] = val
                        changed = True
                return changed

        self.combat_history[norm_lvl].append({
            "timestamp": ts_clean,
            "damage": clean_dmg
        })
        self.combat_history[norm_lvl].sort(key=lambda r: self._parse_timestamp_sort_key(r.get("timestamp", "")))
        if trim:
            self._trim_level_history(norm_lvl)
        return True

    def _merge_existing_excel(self, filepath: str = None) -> bool:
        if not HAS_OPENPYXL:
            return False
        target_xlsx = filepath or os.path.join(BASE_DIR, EXCEL_FILENAME)
        if not os.path.exists(target_xlsx):
            return False

        before_snapshot = {
            k: [(r["timestamp"], dict(r["damage"])) for r in v]
            for k, v in self.combat_history.items()
        }

        wb_old = None
        try:
            wb_old = openpyxl.load_workbook(target_xlsx, data_only=True)
            for sheetname in wb_old.sheetnames:
                if not sheetname.lower().startswith(("nível", "nivel")):
                    continue
                lvl_key = self._normalize_level_key(sheetname)
                ws_old = wb_old[sheetname]
                if ws_old.max_row < 2:
                    continue

                header_row = [cell.value for cell in ws_old[1]]
                if not header_row:
                    continue

                first_col_txt = str(header_row[0] or "").strip()
                if first_col_txt == "# Luta":
                    ts_col_idx = 1
                elif first_col_txt in ("Data/Hora", "Data / Hora"):
                    ts_col_idx = 0
                else:
                    continue

                char_cols = []
                for col_idx in range(ts_col_idx + 1, len(header_row)):
                    h_val = header_row[col_idx]
                    if h_val is None:
                        break
                    h_str = str(h_val).strip()
                    if not h_str or h_str == "Total da Equipe" or h_str.startswith(("📊", "🏆", "★")):
                        break
                    char_cols.append((col_idx, h_str))

                if not char_cols:
                    continue

                for row_vals in ws_old.iter_rows(min_row=2, values_only=True):
                    if not row_vals or len(row_vals) <= ts_col_idx or row_vals[ts_col_idx] is None:
                        continue
                    ts_str = str(row_vals[ts_col_idx]).strip()
                    if not ts_str or ts_str.upper().startswith(("MÉDIA", "MEDIA", "RECORDE", "TOTAL")):
                        continue
                    dmg_dict = {}
                    for col_idx, char_name in char_cols:
                        if col_idx < len(row_vals) and row_vals[col_idx] is not None:
                            try:
                                dmg_dict[char_name] = int(float(row_vals[col_idx]))
                            except (ValueError, TypeError):
                                pass
                    self._add_or_merge_fight_record(lvl_key, ts_str, dmg_dict, trim=False)
        except Exception:
            pass
        finally:
            if wb_old is not None:
                try: wb_old.close()
                except Exception: pass

        for lvl_k in list(self.combat_history.keys()):
            self.combat_history[lvl_k].sort(key=lambda r: self._parse_timestamp_sort_key(r.get("timestamp", "")))
            self._trim_level_history(lvl_k)

        after_snapshot = {
            k: [(r["timestamp"], dict(r["damage"])) for r in v]
            for k, v in self.combat_history.items()
        }
        return after_snapshot != before_snapshot

    def _load_history_db(self):
        with self._history_lock:
            db_path = os.path.join(BASE_DIR, HISTORY_FILENAME)
            try:
                with open(db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for lvl, records in data.items():
                        if isinstance(records, list):
                            for rec in records:
                                if isinstance(rec, dict):
                                    self._add_or_merge_fight_record(lvl, rec.get("timestamp", ""), rec.get("damage", {}), trim=False)
            except Exception:
                pass

            for lvl_k in list(self.combat_history.keys()):
                self.combat_history[lvl_k].sort(key=lambda r: self._parse_timestamp_sort_key(r.get("timestamp", "")))
                self._trim_level_history(lvl_k)

            if self._merge_existing_excel():
                self._save_history_db_unlocked()

    def _save_history_db_unlocked(self):
        db_path = os.path.join(BASE_DIR, HISTORY_FILENAME)
        try:
            for lvl_k in list(self.combat_history.keys()):
                self._trim_level_history(lvl_k)
            with open(db_path, "w", encoding="utf-8") as f:
                json.dump(self.combat_history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _save_history_db(self):
        with self._history_lock:
            self._save_history_db_unlocked()

    def _trigger_level_prompt(self, end_snap):
        self.pending_fight_queue.append(end_snap)

    def _force_window_focus(self, dialog, entry):
        if not dialog or not dialog.winfo_exists():
            return
        try:
            dialog.attributes("-topmost", True)
            dialog.lift()
            if sys.platform == "win32":
                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32
                hwnd = user32.GetParent(dialog.winfo_id()) or dialog.winfo_id()
                fg_hwnd = user32.GetForegroundWindow()
                fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
                cur_tid = kernel32.GetCurrentThreadId()
                attached = False
                if fg_tid and fg_tid != cur_tid:
                    attached = bool(user32.AttachThreadInput(fg_tid, cur_tid, True))
                try:
                    user32.keybd_event(0xFF, 0, 0, 0)
                    user32.keybd_event(0xFF, 0, 2, 0)
                    user32.ShowWindow(hwnd, 5)
                    user32.BringWindowToTop(hwnd)
                    user32.SetForegroundWindow(hwnd)
                    user32.SetActiveWindow(hwnd)
                finally:
                    if attached:
                        user32.AttachThreadInput(fg_tid, cur_tid, False)
            dialog.focus_force()
            entry.focus_force()
            entry.focus_set()
            entry.icursor(tk.END)
            if entry.get():
                entry.select_range(0, tk.END)
        except Exception:
            pass

    def _show_level_dialog(self, end_snap):
        if not end_snap: return
        source = end_snap.get("damage", {})
        active_roster = self._get_active_roster(end_snap)

        totals = {char: sum(source.get(char, {}).values()) for char in active_roster}
        if not totals or max(totals.values(), default=0) == 0:
            return

        if self.level_dialog_window and self.level_dialog_window.winfo_exists():
            try: self.level_dialog_window.destroy()
            except Exception: pass

        dialog = tk.Toplevel(self.root)
        self.level_dialog_window = dialog
        dialog.title("Gravar Combate")
        dialog.config(bg=COLOR_BODY)
        dialog.attributes("-topmost", True)

        dialog_x = self.app_x + (APP_WIDTH // 2) - 125
        offset_y = (DETAILS_HEIGHT + 15) if self.show_details else 10
        dialog_y = self.app_y + APP_HEIGHT + offset_y
        dialog.geometry(f"250x120+{dialog_x}+{dialog_y}")

        icon_path = self._resource_path("icone.ico")
        if os.path.exists(icon_path):
            try: dialog.iconbitmap(icon_path)
            except Exception: pass

        tk.Label(dialog, text="Combate encerrado!\nQual a faixa de nível da luta? (ex: 140)", bg=COLOR_BODY, fg="#fff", font=("Segoe UI", 9)).pack(pady=10)

        entry = tk.Entry(dialog, bg="#2a2a35", fg="#fff", insertbackground="#fff", justify="center", font=("Segoe UI", 10, "bold"))
        entry.pack(pady=5)
        if self.last_entered_level:
            entry.insert(0, self.last_entered_level)
            entry.select_range(0, tk.END)

        action_done = {"flag": False}

        def save(event=None):
            if action_done["flag"]:
                return "break"
            action_done["flag"] = True
            raw_lvl = entry.get().strip()
            try:
                dialog.destroy()
            except Exception:
                pass
            if raw_lvl:
                norm_lvl = self._normalize_level_key(raw_lvl)
                self.last_entered_level = norm_lvl
                self._save_config()
                ts_now = time.strftime("%d/%m/%Y %H:%M:%S")
                with self._history_lock:
                    self._add_or_merge_fight_record(norm_lvl, ts_now, totals, trim=True)
                    self._save_history_db_unlocked()
                threading.Thread(target=self._export_excel, kwargs={"silent": True}, daemon=True).start()
            return "break"

        def skip(event=None):
            if action_done["flag"]:
                return "break"
            action_done["flag"] = True
            try:
                dialog.destroy()
            except Exception:
                pass
            return "break"

        btn_frame = tk.Frame(dialog, bg=COLOR_BODY)
        btn_frame.pack()
        tk.Button(btn_frame, text="Salvar", command=save, bg="#4caf7d", fg="#fff", bd=0, width=10).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Ignorar", command=skip, bg="#e05c5c", fg="#fff", bd=0, width=10).pack(side="left", padx=5)

        entry.bind("<Return>", save)
        entry.bind("<KP_Enter>", save)
        entry.bind("<Escape>", skip)
        dialog.bind("<Return>", save)
        dialog.bind("<KP_Enter>", save)
        dialog.bind("<Escape>", skip)

        dialog.update_idletasks()
        self._force_window_focus(dialog, entry)
        dialog.after(60, lambda: self._force_window_focus(dialog, entry))
        dialog.after(180, lambda: self._force_window_focus(dialog, entry))

    # ============================== EXPORTAÇÃO EXCEL (SIMÉTRICA E CALIBRADA) ==============================

    def _make_txpr_xml(self, size_pt: int, bold: bool = True, color_hex: str = "181920"):
        sz = int(size_pt * 100)
        b_val = "1" if bold else "0"
        return fromstring(
            f'<c:txPr xmlns:c="{C_NS}" xmlns:a="{A_NS}">'
            f'<a:bodyPr/><a:lstStyle/>'
            f'<a:p><a:pPr>'
            f'<a:defRPr sz="{sz}" b="{b_val}">'
            f'<a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>'
            f'<a:latin typeface="Segoe UI"/>'
            f'<a:ea typeface="Segoe UI"/>'
            f'<a:cs typeface="Segoe UI"/>'
            f'</a:defRPr>'
            f'</a:pPr><a:endParaRPr lang="pt-BR" sz="{sz}" b="{b_val}"/></a:p>'
            f'</c:txPr>'
        )

    def _make_rich_title_xml(self, text_str: str, size_pt: int, bold: bool = True, color_hex: str = "181920"):
        sz = int(size_pt * 100)
        b_val = "1" if bold else "0"
        safe_txt = (
            str(text_str)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return fromstring(
            f'<c:title xmlns:c="{C_NS}" xmlns:a="{A_NS}">'
            f'<c:tx><c:rich>'
            f'<a:bodyPr/><a:lstStyle/>'
            f'<a:p>'
            f'<a:pPr><a:defRPr sz="{sz}" b="{b_val}">'
            f'<a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>'
            f'<a:latin typeface="Segoe UI"/>'
            f'<a:ea typeface="Segoe UI"/>'
            f'<a:cs typeface="Segoe UI"/>'
            f'</a:defRPr></a:pPr>'
            f'<a:r>'
            f'<a:rPr lang="pt-BR" sz="{sz}" b="{b_val}">'
            f'<a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>'
            f'<a:latin typeface="Segoe UI"/>'
            f'<a:ea typeface="Segoe UI"/>'
            f'<a:cs typeface="Segoe UI"/>'
            f'</a:rPr>'
            f'<a:t>{safe_txt}</a:t>'
            f'</a:r>'
            f'<a:endParaRPr lang="pt-BR" sz="{sz}" b="{b_val}"/>'
            f'</a:p>'
            f'</c:rich></c:tx>'
            f'<c:layout/><c:overlay val="0"/>'
            f'</c:title>'
        )

    def _replace_title_xml(self, parent_el, text_str: str, size_pt: int, bold: bool = True, color_hex: str = "181920"):
        if parent_el is None:
            return
        new_title = self._make_rich_title_xml(text_str, size_pt, bold=bold, color_hex=color_hex)
        old_title = parent_el.find(f"{{{C_NS}}}title")
        if old_title is not None:
            idx = list(parent_el).index(old_title)
            parent_el.remove(old_title)
            parent_el.insert(idx, new_title)
        else:
            parent_el.insert(0, new_title)

    def _inject_chart_font_xml(self, chart, num_series: int, main_title: str, x_title: str, y_title: str):
        chart.style = None
        orig_to_tree = chart.to_tree

        def custom_to_tree(tagname=None, idx=None, namespace=None):
            tree = orig_to_tree(tagname=tagname, idx=idx, namespace=namespace)
            self._replace_title_xml(tree, main_title, 15, bold=True, color_hex="181920")

            plot_area = tree.find(f"{{{C_NS}}}plotArea")
            if plot_area is not None:
                for ax in plot_area.findall(f"{{{C_NS}}}catAx"):
                    self._replace_title_xml(ax, x_title, 13, bold=True, color_hex="181920")
                    old_txpr = ax.find(f"{{{C_NS}}}txPr")
                    if old_txpr is not None:
                        ax.remove(old_txpr)
                    cross_el = ax.find(f"{{{C_NS}}}crossAx")
                    if cross_el is not None:
                        c_idx = list(ax).index(cross_el)
                        ax.insert(c_idx, self._make_txpr_xml(12, bold=True, color_hex="212529"))
                    else:
                        ax.append(self._make_txpr_xml(12, bold=True, color_hex="212529"))

                for ax in plot_area.findall(f"{{{C_NS}}}valAx"):
                    self._replace_title_xml(ax, y_title, 13, bold=True, color_hex="181920")
                    old_txpr = ax.find(f"{{{C_NS}}}txPr")
                    if old_txpr is not None:
                        ax.remove(old_txpr)
                    cross_el = ax.find(f"{{{C_NS}}}crossAx")
                    if cross_el is not None:
                        c_idx = list(ax).index(cross_el)
                        ax.insert(c_idx, self._make_txpr_xml(12, bold=True, color_hex="212529"))
                    else:
                        ax.append(self._make_txpr_xml(12, bold=True, color_hex="212529"))

            old_leg = tree.find(f"{{{C_NS}}}legend")
            if old_leg is not None:
                leg_idx = list(tree).index(old_leg)
                tree.remove(old_leg)
                new_leg = fromstring(f'<c:legend xmlns:c="{C_NS}"><c:legendPos val="t"/></c:legend>')
                for s_idx in range(num_series):
                    le = fromstring(f'<c:legendEntry xmlns:c="{C_NS}"><c:idx val="{s_idx}"/></c:legendEntry>')
                    le.append(self._make_txpr_xml(14, bold=True, color_hex="181920"))
                    new_leg.append(le)
                new_leg.append(fromstring(f'<c:layout xmlns:c="{C_NS}"/>'))
                new_leg.append(fromstring(f'<c:overlay xmlns:c="{C_NS}" val="0"/>'))
                new_leg.append(self._make_txpr_xml(14, bold=True, color_hex="181920"))
                tree.insert(leg_idx, new_leg)
            return tree

        chart.to_tree = custom_to_tree

    def _set_col_width(self, ws, col_letter: str, width_val: float):
        ws.column_dimensions[col_letter].width = float(width_val)

    def _export_excel(self, silent: bool = True):
        if not HAS_OPENPYXL:
            return

        try:
            filepath = os.path.join(BASE_DIR, EXCEL_FILENAME)
            temp_filepath = os.path.join(BASE_DIR, f"~temp_{EXCEL_FILENAME}")

            with self._history_lock:
                if not self.combat_history and os.path.exists(filepath):
                    if self._merge_existing_excel(filepath):
                        self._save_history_db_unlocked()
                history_snapshot = {
                    lvl: [
                        {"timestamp": r["timestamp"], "damage": dict(r["damage"])}
                        for r in recs[-MAX_FIGHTS_PER_LEVEL:]
                    ]
                    for lvl, recs in self.combat_history.items() if recs
                }

            if not history_snapshot:
                return

            wb = openpyxl.Workbook()
            default_sheet = wb.active

            dark_header_fill = PatternFill(start_color="181920", end_color="181920", fill_type="solid")
            sub_header_fill = PatternFill(start_color="252733", end_color="252733", fill_type="solid")
            zebra_even_fill = PatternFill(start_color="F3F5F9", end_color="F3F5F9", fill_type="solid")
            zebra_odd_fill = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
            mvp_fill = PatternFill(start_color="FFF4CC", end_color="FFF4CC", fill_type="solid")
            record_fill = PatternFill(start_color="DDF3E4", end_color="DDF3E4", fill_type="solid")
            summary_even_fill = PatternFill(start_color="F8F9FC", end_color="F8F9FC", fill_type="solid")

            title_font = CellFont(name="Segoe UI", size=14, bold=True, color="E8C95A")
            white_header_font = CellFont(name="Segoe UI", size=14, bold=True, color="FFFFFF")
            sub_header_font = CellFont(name="Segoe UI", size=13, bold=True, color="FFFFFF")
            idx_font = CellFont(name="Segoe UI", size=13, bold=True, color="495057")
            date_font = CellFont(name="Segoe UI", size=13, bold=True, color="212529")
            num_font = CellFont(name="Segoe UI", size=14, bold=True, color="212529")
            mvp_font = CellFont(name="Segoe UI", size=14, bold=True, color="856404")
            record_font = CellFont(name="Segoe UI", size=14, bold=True, color="155724")
            total_font = CellFont(name="Segoe UI", size=14, bold=True, color="1A1A2E")

            center_align = Alignment(horizontal="center", vertical="center", shrink_to_fit=False)

            thin_side = Side(border_style="thin", color="DCE1E7")
            header_bottom_side = Side(border_style="medium", color="E8C95A")
            cell_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
            header_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=header_bottom_side)

            def sort_level_key(val):
                nums = re.findall(r'\d+', str(val))
                return (int(nums[0]) if nums else 999999, str(val))

            sheets_created = 0
            for lvl in sorted(history_snapshot.keys(), key=sort_level_key):
                fights = history_snapshot[lvl][-MAX_FIGHTS_PER_LEVEL:]
                if not fights:
                    continue

                clean_lvl = self._normalize_level_key(lvl)
                base_title = f"Nível {clean_lvl}"[:31]
                sheet_title = base_title
                suffix = 2
                while sheet_title in wb.sheetnames:
                    sheet_title = f"{base_title[:28]}_{suffix}"
                    suffix += 1

                ws = wb.create_sheet(title=sheet_title)
                ws.views.sheetView[0].showGridLines = False
                ws.freeze_panes = "A2"
                sheets_created += 1

                all_chars = set()
                for f in fights:
                    all_chars.update(f["damage"].keys())
                all_chars = sorted(list(all_chars))
                if not all_chars:
                    continue

                max_per_char = {
                    c: max([int(f["damage"].get(c, 0)) for f in fights], default=0)
                    for c in all_chars
                }

                headers = ["# Luta", "Data / Hora"] + all_chars
                ws.append(headers)
                ws.row_dimensions[1].height = 34

                for col_idx in range(1, len(headers) + 1):
                    c_cell = ws.cell(row=1, column=col_idx)
                    c_cell.alignment = center_align
                    c_cell.border = header_border
                    if col_idx <= 2:
                        c_cell.fill = dark_header_fill
                        c_cell.font = title_font
                    else:
                        cor_hex = EXCEL_CHAR_PALETTE[(col_idx - 3) % len(EXCEL_CHAR_PALETTE)]
                        c_cell.fill = PatternFill(start_color=cor_hex, end_color=cor_hex, fill_type="solid")
                        c_cell.font = white_header_font

                for fight_num, f in enumerate(fights, start=1):
                    row_idx = fight_num + 1
                    ts_val = f.get("timestamp", "")
                    char_vals = [int(f["damage"].get(c, 0)) for c in all_chars]
                    fight_top_dmg = max(char_vals, default=0)

                    row_data = [f"#{fight_num:02d}", ts_val] + char_vals
                    ws.append(row_data)
                    ws.row_dimensions[row_idx].height = 28

                    base_fill = zebra_even_fill if (row_idx % 2 == 0) else zebra_odd_fill
                    for col_idx in range(1, len(row_data) + 1):
                        d_cell = ws.cell(row=row_idx, column=col_idx)
                        d_cell.border = cell_border
                        d_cell.alignment = center_align
                        if col_idx == 1:
                            d_cell.fill = base_fill
                            d_cell.font = idx_font
                        elif col_idx == 2:
                            d_cell.fill = base_fill
                            d_cell.font = date_font
                        else:
                            c_name = all_chars[col_idx - 3]
                            val = char_vals[col_idx - 3]
                            d_cell.number_format = "#,##0"
                            if val > 0 and val == max_per_char[c_name]:
                                d_cell.fill = record_fill
                                d_cell.font = record_font
                            elif val > 0 and val == fight_top_dmg:
                                d_cell.fill = mvp_fill
                                d_cell.font = mvp_font
                            else:
                                d_cell.fill = base_fill
                                d_cell.font = num_font

                summary_start_col = len(headers) + 2
                summary_end_col = summary_start_col + 4

                ws.merge_cells(
                    start_row=1, start_column=summary_start_col,
                    end_row=1, end_column=summary_end_col
                )
                title_cell = ws.cell(row=1, column=summary_start_col)
                title_cell.value = f"★ RESUMO INDIVIDUAL - NÍVEL {clean_lvl} (ÚLTIMAS {len(fights)}/{MAX_FIGHTS_PER_LEVEL} LUTAS)"
                for col_idx in range(summary_start_col, summary_end_col + 1):
                    m_cell = ws.cell(row=1, column=col_idx)
                    m_cell.fill = dark_header_fill
                    m_cell.font = title_font
                    m_cell.alignment = center_align
                    m_cell.border = header_border

                summary_headers = ["Personagem", "Lutas", "Média / Luta", "Recorde (Máx)", "Total Acumulado"]
                ws.row_dimensions[2].height = max(ws.row_dimensions[2].height or 28, 30)
                for offset, sh_text in enumerate(summary_headers):
                    sh_cell = ws.cell(row=2, column=summary_start_col + offset, value=sh_text)
                    sh_cell.fill = sub_header_fill
                    sh_cell.font = sub_header_font
                    sh_cell.alignment = center_align
                    sh_cell.border = cell_border

                for i_char, c_name in enumerate(all_chars):
                    c_idx = i_char + 3
                    ws.row_dimensions[c_idx].height = max(ws.row_dimensions[c_idx].height or 28, 30)
                    c_all_vals = [int(f["damage"].get(c_name, 0)) for f in fights]
                    c_active_vals = [v for v in c_all_vals if v > 0]
                    c_fights_count = len(c_active_vals) if c_active_vals else len(c_all_vals)
                    c_total = sum(c_all_vals)
                    c_avg = round(c_total / len(c_active_vals)) if c_active_vals else 0
                    c_max = max(c_all_vals) if c_all_vals else 0

                    cor_char = EXCEL_CHAR_PALETTE[i_char % len(EXCEL_CHAR_PALETTE)]
                    row_bg = summary_even_fill if (i_char % 2 == 0) else zebra_odd_fill

                    s_vals = [c_name, c_fights_count, c_avg, c_max, c_total]
                    for offset, s_val in enumerate(s_vals):
                        sc = ws.cell(row=c_idx, column=summary_start_col + offset, value=s_val)
                        sc.border = cell_border
                        sc.alignment = center_align
                        if offset == 0:
                            sc.fill = PatternFill(start_color=cor_char, end_color=cor_char, fill_type="solid")
                            sc.font = white_header_font
                        elif offset == 3:
                            sc.fill = record_fill
                            sc.font = record_font
                            sc.number_format = "#,##0"
                        elif offset == 4:
                            sc.fill = mvp_fill
                            sc.font = total_font
                            sc.number_format = "#,##0"
                        else:
                            sc.fill = row_bg
                            sc.font = num_font
                            sc.number_format = "#,##0"

                leg_row = len(all_chars) + 4
                ws.row_dimensions[leg_row].height = max(ws.row_dimensions[leg_row].height or 28, 28)
                ws.merge_cells(start_row=leg_row, start_column=summary_start_col, end_row=leg_row, end_column=summary_end_col)
                leg_cell = ws.cell(
                    row=leg_row, column=summary_start_col,
                    value=f"Legenda:  [★ Dourado = Maior Dano da Luta]   [▲ Verde = Recorde Pessoal]   (Limite: {MAX_FIGHTS_PER_LEVEL} Lutas)"
                )
                leg_cell.font = CellFont(name="Segoe UI", size=11, bold=True, color="212529")
                leg_cell.alignment = center_align

                self._set_col_width(ws, "A", 12)
                self._set_col_width(ws, "B", 26)
                max_char_name_len = max([len(str(c)) for c in all_chars], default=16)
                char_col_w = max(26, int(max_char_name_len * 1.45) + 6)

                for idx in range(3, len(all_chars) + 3):
                    col_letter = get_column_letter(idx)
                    c_len = len(str(headers[idx - 1]))
                    self._set_col_width(ws, col_letter, max(25, int(c_len * 1.45) + 6))

                self._set_col_width(ws, get_column_letter(len(headers) + 1), 3)

                summary_widths = [char_col_w, 12, 19, 20, 23]
                for offset, width_val in enumerate(summary_widths):
                    col_letter = get_column_letter(summary_start_col + offset)
                    self._set_col_width(ws, col_letter, width_val)

                data_ref = Reference(ws, min_col=3, min_row=1, max_row=len(fights) + 1, max_col=2 + len(all_chars))
                cats_ref = Reference(ws, min_col=1, min_row=2, max_row=len(fights) + 1)
                chart_anchor_col = get_column_letter(summary_start_col)
                chart1_start_row = len(all_chars) + 6

                line_title_str = f"Evolução de Dano Individual (Últimas {len(fights)} Lutas) - Nível {clean_lvl}"
                line_chart = LineChart()
                line_chart.title = line_title_str
                line_chart.y_axis.title = "Dano Causado"
                line_chart.x_axis.title = "Número da Luta (#)"
                line_chart.add_data(data_ref, titles_from_data=True)
                line_chart.set_categories(cats_ref)
                line_chart.width = 24
                line_chart.height = 12.5

                for idx_s, serie in enumerate(line_chart.series):
                    cor_hex = EXCEL_CHAR_PALETTE[idx_s % len(EXCEL_CHAR_PALETTE)]
                    serie.graphicalProperties.line.solidFill = cor_hex
                    serie.graphicalProperties.line.width = 30000
                    serie.smooth = True
                    serie.marker.symbol = "circle"
                    serie.marker.size = 8
                    serie.marker.graphicalProperties.solidFill = cor_hex
                    serie.marker.graphicalProperties.line.solidFill = "FFFFFF"

                self._inject_chart_font_xml(line_chart, len(all_chars), line_title_str, "Número da Luta (#)", "Dano Causado")
                ws.add_chart(line_chart, f"{chart_anchor_col}{chart1_start_row}")

                bar_title_str = f"Comparativo Direto por Combate - Nível {clean_lvl}"
                bar_chart = BarChart()
                bar_chart.type = "col"
                bar_chart.grouping = "clustered"
                bar_chart.overlap = -15
                bar_chart.gapWidth = 130
                bar_chart.title = bar_title_str
                bar_chart.y_axis.title = "Dano Causado"
                bar_chart.x_axis.title = "Número da Luta (#)"
                bar_chart.add_data(data_ref, titles_from_data=True)
                bar_chart.set_categories(cats_ref)
                bar_chart.width = 24
                bar_chart.height = 12.5

                for idx_s, serie in enumerate(bar_chart.series):
                    cor_hex = EXCEL_CHAR_PALETTE[idx_s % len(EXCEL_CHAR_PALETTE)]
                    serie.graphicalProperties.solidFill = cor_hex
                    serie.graphicalProperties.line.solidFill = cor_hex

                self._inject_chart_font_xml(bar_chart, len(all_chars), bar_title_str, "Número da Luta (#)", "Dano Causado")
                ws.add_chart(bar_chart, f"{chart_anchor_col}{chart1_start_row + 24}")

            if sheets_created == 0:
                return

            if default_sheet in wb.worksheets:
                wb.remove(default_sheet)

            with self._history_lock:
                try:
                    wb.save(temp_filepath)
                    os.replace(temp_filepath, filepath)
                except PermissionError:
                    if os.path.exists(temp_filepath):
                        try: os.remove(temp_filepath)
                        except Exception: pass
        except Exception:
            pass

    # ============================== AUTO UPDATER ==============================

    def _is_newer_version(self, latest, current):
        def parse_v(version_string):
            parts = re.findall(r'(\d+|[a-zA-Z]+)', str(version_string))
            return [int(p) if p.isdigit() else p.lower() for p in parts]

        v_latest = parse_v(latest)
        v_current = parse_v(current)

        max_len = max(len(v_latest), len(v_current))
        while len(v_latest) < max_len: v_latest.append(0)
        while len(v_current) < max_len: v_current.append(0)

        for l, c in zip(v_latest, v_current):
            if type(l) != type(c):
                return str(l) > str(c)
            if l > c: return True
            if l < c: return False
        return False

    def _check_for_updates(self):
        if not UPDATE_JSON_URL.startswith("http"): return
        try:
            url_with_cachebuster = f"{UPDATE_JSON_URL}?t={int(time.time())}"
            req = urllib.request.Request(url_with_cachebuster, headers={
                'User-Agent': 'WakfuDamageMeterUpdater',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))

            latest_version = data.get("version")
            download_url = data.get("download_url")

            if latest_version and self._is_newer_version(latest_version, APP_VERSION):
                self.root.after(2000, lambda: self._ask_update(latest_version, download_url))
        except Exception:
            pass

    def _ask_update(self, latest_version, download_url):
        self._modal_dialog_open = True
        try:
            ans = messagebox.askyesno("Atualização Disponível",
                f"Uma nova versão ({latest_version}) do Wakfu Damage Meter está disponível!\n\nDeseja baixar e instalar agora automaticamente?")
        finally:
            self._modal_dialog_open = False
        if ans:
            dl_window = tk.Toplevel(self.root)
            dl_window.title("Atualizando...")
            dl_window.geometry("300x100")
            dl_window.configure(bg=COLOR_BODY)
            dl_window.attributes("-topmost", True)
            tk.Label(dl_window, text="Baixando e instalando atualização...\nPor favor, aguarde.", bg=COLOR_BODY, fg="#ffffff").pack(expand=True)
            threading.Thread(target=self._perform_update, args=(download_url, dl_window), daemon=True).start()

    def _perform_update(self, download_url, dl_window):
        try:
            zip_path = os.path.join(BASE_DIR, "update_temp.zip")
            extract_path = os.path.join(BASE_DIR, "update_temp_dir")
            bat_path = os.path.join(BASE_DIR, "atualizador_ninja.bat")

            req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)

            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)
            os.makedirs(extract_path)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            bat_content = f"""@echo off
cd /d "{BASE_DIR}"
title Wakfu Damage Meter - Instalador
echo ===================================================
echo Instalando a nova versao...
echo O processo levara apenas alguns segundos.
echo ===================================================
timeout /t 3 /nobreak > NUL

xcopy /E /Y /C "update_temp_dir\\Wakfu Damage Meter\\*" ".\\*"

rmdir /S /Q "update_temp_dir"
del "update_temp.zip"

start "" "Wakfu Damage Meter.exe"
del "%~f0"
"""
            with open(bat_path, "w", encoding="utf-8") as bat_file:
                bat_file.write(bat_content)

            os.startfile(bat_path)
            self.root.after(0, self._quit_app)

        except Exception as e:
            err_msg = str(e)
            def _on_err():
                try:
                    if dl_window and dl_window.winfo_exists():
                        dl_window.destroy()
                except Exception:
                    pass
                messagebox.showerror("Erro de Atualização", f"Ocorreu um erro ao atualizar: {err_msg}")
            self.root.after(0, _on_err)

    # =========================================================================

    def _resource_path(self, relative_path):
        paths_to_try = []
        if hasattr(sys, '_MEIPASS'):
            paths_to_try.append(os.path.join(sys._MEIPASS, relative_path))
        paths_to_try.append(os.path.join(BASE_DIR, relative_path))
        paths_to_try.append(os.path.join(os.path.dirname(sys.executable), relative_path))

        for p in paths_to_try:
            if os.path.exists(p):
                return p
        return os.path.join(BASE_DIR, relative_path)

    def _apply_opacity(self):
        alpha = self.opacity_var.get() / 100
        self.bg_window.attributes("-alpha", alpha)
        self.details_bg.attributes("-alpha", alpha)

    def _apply_window_region(self):
        if sys.platform == "win32":
            try:
                gdi32 = ctypes.windll.gdi32
                user32 = ctypes.windll.user32
                for win, h in (
                    (self.root, APP_HEIGHT),
                    (self.bg_window, APP_HEIGHT),
                    (self.details_root, DETAILS_HEIGHT),
                    (self.details_bg, DETAILS_HEIGHT),
                ):
                    hwnd = user32.GetParent(win.winfo_id())
                    if hwnd:
                        rgn = gdi32.CreateRoundRectRgn(0, 0, APP_WIDTH, h, 15, 15)
                        if not user32.SetWindowRgn(hwnd, rgn, True):
                            gdi32.DeleteObject(rgn)
            except Exception:
                pass

    def _create_rounded_bg(self, w, h, radius, fill, outline=None, width=0):
        img = Image.new("RGBA", (w, h), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        offset = width // 2
        draw.rounded_rectangle(
            (offset, offset, w - 1 - offset, h - 1 - offset),
            radius, fill=fill, outline=outline, width=width
        )
        return ImageTk.PhotoImage(img)

    def _load_config(self):
        try:
            with open(self._config_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            self.included_chars = set(data.get("included_characters", []))
            self.roster = set(data.get("roster", list(self.included_chars)))
            if "log_path" in data: self.log_path_var.set(data["log_path"])
            if "hotkey" in data: self.hotkey_var.set(data["hotkey"])
            if "last_level" in data: self.last_entered_level = str(data["last_level"])
            self.opacity_var.set(max(10, min(100, int(data.get("opacity_percent", 10)))))

            if data.get("schema_version") == CONFIG_SCHEMA_VERSION:
                known_classes = data.get("known_classes", {})
                known_ai = data.get("known_ai", {})
                self.state.load_persisted_classes(known_classes, known_ai)
        except Exception: pass

    def _save_config(self):
        try:
            snap = self.state.snapshot()
            summons = set(snap.get("summon_owner", {}).keys()) | ROUBLARD_BOMBS | SRAM_DOUBLES | ZOBAL_CLONES
            ai_map = snap.get("is_ai_controlled", {})
            class_map = snap.get("character_class", {})
            known_classes = {
                k: v for k, v in class_map.items()
                if k not in summons and v in CLASS_MAP and ai_map.get(k) is False
            }
            known_ai = {
                k: False for k, v in ai_map.items()
                if k not in summons and v is False and class_map.get(k) in CLASS_MAP
            }
            with open(self._config_path(), "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": CONFIG_SCHEMA_VERSION,
                    "included_characters": sorted(list(self.included_chars)),
                    "roster": sorted(list(self.roster)),
                    "opacity_percent": self.opacity_var.get(),
                    "log_path": self.log_path_var.get(),
                    "hotkey": self.hotkey_var.get(),
                    "last_level": self.last_entered_level,
                    "known_classes": known_classes,
                    "known_ai": known_ai
                }, f, ensure_ascii=False, indent=2)
        except Exception: pass

    def _config_path(self) -> str:
        return os.path.join(BASE_DIR, CONFIG_FILENAME)

    def _build_unified_ui(self):
        self.canvas = tk.Canvas(self.root, width=APP_WIDTH, height=APP_HEIGHT, bg=CHROMA_KEY, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.canvas.create_image(0, 0, image=self.img_header_bg, anchor="nw")
        self.canvas.create_text(440, 17, text="⚙", fill=TEXT_GRAY, font=("Segoe UI", 11), anchor="center")
        self.canvas.create_text(460, 17, text="✕", fill=TEXT_GRAY, font=("Segoe UI", 10), anchor="center")
        self.canvas.bind("<Button-1>", self._on_canvas_click)

        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)

        self.details_canvas = tk.Canvas(self.details_root, width=APP_WIDTH, height=DETAILS_HEIGHT, bg=CHROMA_KEY, highlightthickness=0)
        self.details_canvas.pack(fill="both", expand=True)

        self.details_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.details_canvas.bind("<Button-4>", self._on_mousewheel)
        self.details_canvas.bind("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if not self.show_details: return
        if event.num == 5 or event.delta < 0:
            self.details_scroll_y += 30
        if event.num == 4 or event.delta > 0:
            self.details_scroll_y -= 30

        self.details_scroll_y = max(0, min(self.details_scroll_y, self.max_scroll))
        self._last_state_hash = None

    def _sync_windows(self, x=None, y=None):
        if x is not None: self.app_x = x
        if y is not None: self.app_y = y

        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}+{self.app_x}+{self.app_y}")
        self.bg_window.geometry(f"{APP_WIDTH}x{APP_HEIGHT}+{self.app_x}+{self.app_y}")

        det_y = self.app_y + APP_HEIGHT + 5
        self.details_root.geometry(f"{APP_WIDTH}x{DETAILS_HEIGHT}+{self.app_x}+{det_y}")
        self.details_bg.geometry(f"{APP_WIDTH}x{DETAILS_HEIGHT}+{self.app_x}+{det_y}")

        if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.geometry(f"350x420+{self.app_x}+{det_y}")

        if hasattr(self, 'level_dialog_window') and self.level_dialog_window and self.level_dialog_window.winfo_exists():
            dialog_x = self.app_x + (APP_WIDTH // 2) - 125
            offset_y = (DETAILS_HEIGHT + 15) if self.show_details else 10
            dialog_y = self.app_y + APP_HEIGHT + offset_y
            self.level_dialog_window.geometry(f"250x120+{dialog_x}+{dialog_y}")

    def _toggle_details(self):
        self.show_details = not self.show_details
        if self.show_details:
            self.details_scroll_y = 0
            self.details_bg.deiconify()
            self.details_root.deiconify()
            self._sync_windows()
            self.details_bg.lift()
            self.details_root.lift()
        else:
            self.details_bg.withdraw()
            self.details_root.withdraw()
            self._sync_windows()
        self._last_state_hash = None

    def _on_canvas_click(self, event):
        x, y = event.x, event.y
        if y <= 35:
            if 5 <= x <= 80: self.mode_var.set("Causado")
            elif 81 <= x <= 150: self.mode_var.set("Recebido")
            elif 151 <= x <= 215: self.mode_var.set("Cura")
            elif 216 <= x <= 290: self.mode_var.set("Armadura")
            elif 291 <= x <= 360:
                snap = self.state.snapshot()
                if snap.get("last_fight_data"):
                    self.view_last_fight = not self.view_last_fight
                else:
                    self.view_last_fight = False
                self.selected_char = None
                self._last_state_hash = None
            elif 361 <= x <= 425:
                self._toggle_details()
            elif 426 <= x <= 450:
                self._open_settings()
            elif 451 <= x <= 475:
                self._quit_app()

            self._last_state_hash = None
        else:
            snap = self.state.snapshot()
            data_context = self._get_target_state_data(snap)
            active_roster = self._get_active_roster(data_context, full_snap=snap)
            display_order = sorted(list(active_roster))[:6]

            for i, name in enumerate(display_order):
                base_x = 20 + (i * 75)
                if base_x <= x <= base_x + 60:
                    self.selected_char = name
                    self.details_scroll_y = 0
                    if not self.show_details:
                        self._toggle_details()
                    self._last_state_hash = None
                    break

    def _strip_accents_lower(self, s: str) -> str:
        if not s:
            return ""
        return "".join(
            c for c in unicodedata.normalize("NFD", str(s))
            if unicodedata.category(c) != "Mn"
        ).strip().lower()

    def _find_avatar_file(self, name: str, breed_id: str = None):
        search_names = []
        if name:
            search_names.append(str(name))
        if breed_id:
            b_str = str(breed_id).strip()
            class_names = CLASS_MAP.get(b_str)
            if class_names:
                search_names.extend(class_names)
            search_names.append(b_str)

        avatar_dirs = [AVATAR_DIR]
        bundled_av = self._resource_path("avatares")
        if os.path.isdir(bundled_av) and os.path.abspath(bundled_av) != os.path.abspath(AVATAR_DIR):
            avatar_dirs.append(bundled_av)

        valid_exts = (".png", ".jpg", ".jpeg", ".webp")

        for av_dir in avatar_dirs:
            if not os.path.isdir(av_dir):
                continue
            for s_name in search_names:
                for ext in valid_exts:
                    p = os.path.join(av_dir, s_name + ext)
                    if os.path.isfile(p):
                        return p

            try:
                files_in_dir = os.listdir(av_dir)
            except OSError:
                continue

            normalized_targets = [self._strip_accents_lower(s) for s in search_names if s]
            for target_norm in normalized_targets:
                for fname in files_in_dir:
                    root_name, ext = os.path.splitext(fname)
                    if ext.lower() not in valid_exts:
                        continue
                    if self._strip_accents_lower(root_name) == target_norm:
                        return os.path.join(av_dir, fname)

        return None

    def _get_avatar(self, name, size, breed_id=None):
        b_key = str(breed_id).strip() if breed_id else None
        cache_key = (name, b_key, size)
        if cache_key in self._avatar_cache:
            return self._avatar_cache[cache_key]

        img_path = self._find_avatar_file(name, b_key)
        is_fallback = False

        if img_path:
            try:
                img = Image.open(img_path).convert("RGBA")
                img = ImageOps.fit(img, (size, size), method=Image.Resampling.LANCZOS)
                mask = Image.new("L", (size, size), 0)
                draw = ImageDraw.Draw(mask)
                draw.rounded_rectangle((0, 0, size-1, size-1), 4, fill=255)
                rounded_img = Image.new("RGBA", (size, size), (0,0,0,0))
                rounded_img.paste(img, (0, 0), mask=mask)
                img = rounded_img
            except Exception:
                img = self._generate_fallback_avatar(name, size)
                is_fallback = True
        else:
            img = self._generate_fallback_avatar(name, size)
            is_fallback = True

        tk_img = ImageTk.PhotoImage(img)
        # Nunca salva no cache se for fallback (quadrado colorido com letra inicial),
        # garantindo que assim que a classe/imagem for identificada ela carregue na hora!
        if not is_fallback:
            self._avatar_cache[cache_key] = tk_img
        return tk_img

    def _generate_fallback_avatar(self, name, size):
        colors = ["#7c5cff", "#4caf7d", "#e05c5c", "#4ea1d3", "#e0a13d"]
        idx = sum(ord(c) for c in name) % len(colors) if name else 0
        color = colors[idx]

        img = Image.new("RGBA", (size, size), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((0, 0, size-1, size-1), 4, fill=color)
        text = name[0].upper() if name else "?"
        draw.text((size//2 - 4, size//2 - 7), text, fill="#ffffff")
        return img

    def _format_num(self, val):
        if val == 0: return "0"
        return f"{val:,}".replace(",", " ")

    def _refresh_loop(self):
        if self.pending_clickthrough_toggle:
            self.pending_clickthrough_toggle = False
            self._toggle_clickthrough()

        if self.pending_config_save:
            self.pending_config_save = False
            self._save_config()

        if self.pending_fight_start:
            self.pending_fight_start = False
            if self.view_last_fight:
                self.view_last_fight = False
                self.selected_char = None
                self._last_state_hash = None

        dialog_open = (
            self.level_dialog_window is not None
            and self.level_dialog_window.winfo_exists()
        )
        if self.pending_fight_queue and not dialog_open:
            snap_to_process = self.pending_fight_queue.pop(0)
            self._show_level_dialog(snap_to_process)
            dialog_open = (
                self.level_dialog_window is not None
                and self.level_dialog_window.winfo_exists()
            )

        if not self.clickthrough and not self._modal_dialog_open:
            if dialog_open:
                self.level_dialog_window.attributes("-topmost", True)
                self.level_dialog_window.lift()
            else:
                self.bg_window.attributes("-topmost", True)
                self.root.attributes("-topmost", True)
                self.bg_window.lift()
                self.root.lift()
                if self.show_details:
                    self.details_bg.attributes("-topmost", True)
                    self.details_root.attributes("-topmost", True)
                    self.details_bg.lift()
                    self.details_root.lift()

                if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.winfo_exists():
                    self.settings_window.attributes("-topmost", True)
                    self.settings_window.lift()

        try:
            snap = self.state.snapshot()
            self._update_bar(snap)
        except Exception:
            pass

        self.root.after(250, self._refresh_loop)

    def _get_target_state_data(self, snap):
        if self.view_last_fight:
            return snap.get("last_fight_data") or {}
        return snap

    def _current_source(self, data_context):
        mode = self.mode_var.get()
        if mode == "Recebido": return data_context.get("received", {})
        if mode == "Cura": return data_context.get("healing", {})
        if mode == "Armadura": return data_context.get("armor", {})
        return data_context.get("damage", {})

    def _get_active_roster(self, data_context, full_snap=None):
        active_roster = set()
        if not data_context:
            return active_roster
        if full_snap is None:
            full_snap = self.state.snapshot()
        char_class_dict = {**full_snap.get("character_class", {}), **(data_context.get("character_class") or {})}
        ai_dict = {**full_snap.get("is_ai_controlled", {}), **(data_context.get("is_ai_controlled") or {})}
        combatants = set(data_context.get("current_combatants", set()))
        summons = (set(data_context.get("summon_owner", {}).keys()) | ROUBLARD_BOMBS | SRAM_DOUBLES | ZOBAL_CLONES) - combatants

        candidates = combatants | set(data_context.get("characters", set()))
        for name in candidates:
            if name in self.included_chars or name in combatants:
                active_roster.add(name)
                continue
            if name in summons:
                continue
            is_ai = ai_dict.get(name)
            breed = char_class_dict.get(name)
            if is_ai is False:
                active_roster.add(name)
            elif is_ai is None and breed in CLASS_MAP:
                active_roster.add(name)

        return active_roster

    def _update_bar(self, snap):
        data_context = self._get_target_state_data(snap)
        source = self._current_source(data_context)
        active_roster = self._get_active_roster(data_context, full_snap=snap)
        char_class_dict = {**snap.get("character_class", {}), **(data_context.get("character_class") or {})}

        totals = {char: sum(source.get(char, {}).values()) for char in active_roster}
        roster_breeds = tuple((c, char_class_dict.get(c)) for c in sorted(active_roster))

        current_hash = (
            snap["version"], self.mode_var.get(),
            roster_breeds, tuple(sorted(totals.items())),
            self.clickthrough, self.show_details, self.selected_char,
            self.details_scroll_y, self.view_last_fight
        )
        if current_hash == self._last_state_hash: return
        self._last_state_hash = current_hash

        self.canvas.delete("dynamic")
        self._active_card_avatars.clear()

        tab_coords = {"Causado": ("", 45), "Recebido": ("", 120), "Cura": ("", 185), "Armadura": ("", 255)}
        active_mode = self.mode_var.get()
        active_x = tab_coords.get(active_mode, ("", 45))[1]

        self.canvas.create_image(active_x, 17, image=self.img_pill_active, anchor="center", tags="dynamic")

        for t_name, (t_disp, t_x) in tab_coords.items():
            color = TEXT_YELLOW if t_name == active_mode else TEXT_GRAY
            self.canvas.create_text(t_x, 17, text=t_name, fill=color, font=("Segoe UI", 9, "bold"), anchor="center", tags="dynamic")

        hist_color = "#4caf7d" if self.view_last_fight else TEXT_GRAY
        self.canvas.create_text(325, 17, text="⏳ Passado", fill=hist_color, font=("Segoe UI", 9, "bold"), anchor="center", tags="dynamic")

        det_color = TEXT_YELLOW if self.show_details else TEXT_GRAY
        self.canvas.create_text(395, 17, text="📊 Detalhes", fill=det_color, font=("Segoe UI", 9, "bold"), anchor="center", tags="dynamic")

        if active_roster:
            max_val = max(totals.values()) if totals else 0
            display_order = sorted(list(active_roster))[:6]

            for i, name in enumerate(display_order):
                val = totals.get(name, 0)
                is_mvp = (val > 0 and val == max_val)

                base_x = 20 + (i * 75)
                base_y = 42

                card_bg = self.img_card_mvp if is_mvp else self.img_card_normal
                self.canvas.create_image(base_x, base_y, image=card_bg, anchor="nw", tags="dynamic")

                breed_id = char_class_dict.get(name)
                tk_avatar = self._get_avatar(name, size=50, breed_id=breed_id)
                self._active_card_avatars.append(tk_avatar)
                self.canvas.create_image(base_x + 5, base_y + 5, image=tk_avatar, anchor="nw", tags="dynamic")

                self.canvas.create_text(base_x + 30, base_y + 65, text=self._format_num(val), fill=TEXT_YELLOW, font=("Segoe UI", 9, "bold"), anchor="center", tags="dynamic")

        if self.show_details:
            self.details_canvas.delete("dynamic_det")

            self.details_canvas.create_image(0, 0, image=self.img_details_bg, anchor="nw", tags="dynamic_det")

            target_char = self.selected_char
            if target_char not in active_roster and active_roster:
                target_char = max(active_roster, key=lambda c: totals.get(c, 0))

            if target_char:
                char_data = source.get(target_char, {})
                sorted_turns = sorted(char_data.items())
                total_val = sum(v for k, v in sorted_turns)
                total_turns = len(sorted_turns)
                avg = total_val // total_turns if total_turns > 0 else 0

                list_start_y = 65
                row_h = 28
                visible_h = DETAILS_HEIGHT - list_start_y - 10

                self.max_scroll = max(0, (total_turns * row_h) - visible_h)
                self.details_scroll_y = max(0, min(self.details_scroll_y, self.max_scroll))

                if total_turns == 0:
                    self.details_canvas.create_text(APP_WIDTH//2, list_start_y + 30, text="Aguardando ações em combate...", fill=TEXT_GRAY, font=("Segoe UI", 9), anchor="center", tags="dynamic_det")
                else:
                    max_turn_val = max(v for k, v in sorted_turns) if sorted_turns else 1
                    if max_turn_val == 0: max_turn_val = 1

                    for i, (turn_idx, turn_val) in enumerate(sorted_turns):
                        y = list_start_y + (i * row_h) - self.details_scroll_y

                        if y < list_start_y - row_h or y > DETAILS_HEIGHT:
                            continue

                        if i % 2 == 0:
                            self.details_canvas.create_rectangle(15, y, APP_WIDTH - 15, y + row_h, fill="#222222", outline="", tags="dynamic_det")

                        self.details_canvas.create_text(25, y + row_h//2, text=f"T. {turn_idx}", fill=TEXT_GRAY, font=("Segoe UI", 9), anchor="w", tags="dynamic_det")
                        self.details_canvas.create_text(75, y + row_h//2, text=self._format_num(turn_val), fill="#ffffff", font=("Segoe UI", 9, "bold"), anchor="w", tags="dynamic_det")

                        bar_max_w = 200
                        bar_w = int((turn_val / max_turn_val) * bar_max_w)
                        self.details_canvas.create_rectangle(160, y + 10, 160 + bar_max_w, y + row_h - 10, fill="#151515", outline="", tags="dynamic_det")
                        if bar_w > 0:
                            self.details_canvas.create_rectangle(160, y + 10, 160 + bar_w, y + row_h - 10, fill=TEXT_YELLOW, outline="", tags="dynamic_det")

                        pct = int((turn_val / total_val) * 100) if total_val > 0 else 0
                        self.details_canvas.create_text(370, y + row_h//2, text=f"{pct}%", fill=TEXT_GRAY, font=("Segoe UI", 8), anchor="w", tags="dynamic_det")

                self.details_canvas.create_rectangle(0, 0, APP_WIDTH, list_start_y - 5, fill=COLOR_HEADER, outline="", tags="dynamic_det")
                title_color = "#4caf7d" if self.view_last_fight else TEXT_YELLOW
                self.details_canvas.create_text(20, 18, text=f"📊 Estatísticas: {target_char}", fill=title_color, font=("Segoe UI", 10, "bold"), anchor="w", tags="dynamic_det")
                self.details_canvas.create_text(20, 40, text=f"Total: {self._format_num(total_val)}  |  Média: {self._format_num(avg)} / turno", fill="#ffffff", font=("Segoe UI", 9), anchor="w", tags="dynamic_det")

            else:
                self.details_canvas.create_text(APP_WIDTH//2, DETAILS_HEIGHT//2, text="Nenhum personagem ativo para análise.", fill=TEXT_GRAY, font=("Segoe UI", 9), anchor="center", tags="dynamic_det")

    def _open_settings(self):
        if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return

        self._last_state_hash = None

        tw = tk.Toplevel(self.root)
        self.settings_window = tw
        tw.title("Configurações")

        icon_path = self._resource_path("icone.ico")
        if os.path.exists(icon_path):
            try: tw.iconbitmap(icon_path)
            except Exception: pass

        det_y = self.app_y + APP_HEIGHT + 5
        tw.geometry(f"350x420+{self.app_x}+{det_y}")

        tw.configure(bg="#1a1a20")
        tw.attributes("-topmost", True)

        tk.Label(tw, text="Pasta do Log:", bg="#1a1a20", fg="#aaa").pack(anchor="w", padx=10, pady=(10,0))
        path_frame = tk.Frame(tw, bg="#1a1a20")
        path_frame.pack(fill="x", padx=10, pady=2)
        tk.Entry(path_frame, textvariable=self.log_path_var, bg="#2a2a35", fg="#fff", insertbackground="#fff").pack(side="left", fill="x", expand=True)
        tk.Button(path_frame, text="...", command=lambda: self._choose_path(tw), bg="#333", fg="#fff", bd=0).pack(side="left", padx=(5,0))

        tk.Label(tw, text="Opacidade do Fundo (%):", bg="#1a1a20", fg="#aaa").pack(anchor="w", padx=10, pady=(10,0))
        tk.Scale(tw, from_=10, to=100, orient="horizontal", variable=self.opacity_var, command=self._on_opacity_change, bg="#1a1a20", fg="#fff", highlightthickness=0).pack(fill="x", padx=10)

        tk.Label(tw, text="Atalho (Click-through):", bg="#1a1a20", fg="#aaa").pack(anchor="w", padx=10, pady=(10,0))
        hk_frame = tk.Frame(tw, bg="#1a1a20")
        hk_frame.pack(fill="x", padx=10, pady=2)
        hk_entry = tk.Entry(hk_frame, textvariable=self.hotkey_var, bg="#2a2a35", fg="#fff", insertbackground="#fff")
        hk_entry.pack(side="left", fill="x", expand=True)
        tk.Button(hk_frame, text="Salvar", command=self._update_custom_hotkey, bg="#333", fg="#fff", bd=0).pack(side="left", padx=(5,0))

        tk.Label(tw, text="Companheiros (Heróis são automáticos):", bg="#1a1a20", fg=TEXT_YELLOW, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(15,0))

        add_frame = tk.Frame(tw, bg="#1a1a20")
        add_frame.pack(fill="x", padx=10, pady=2)
        new_char_var = tk.StringVar()
        entry = tk.Entry(add_frame, textvariable=new_char_var, bg="#2a2a35", fg="#fff")
        entry.pack(side="left", fill="x", expand=True)

        def add_char():
            name = new_char_var.get().strip()
            if name:
                self.included_chars.add(name)
                self.roster.add(name)
                new_char_var.set("")
                self._save_config()
                self._last_state_hash = None
                refresh_list()

        tk.Button(add_frame, text="Adicionar", command=add_char, bg="#4caf7d", fg="#fff", bd=0).pack(side="left", padx=(5,0))
        entry.bind("<Return>", lambda e: add_char())

        list_frame = tk.Frame(tw, bg="#1a1a20")
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        def refresh_list():
            for widget in list_frame.winfo_children(): widget.destroy()
            for name in sorted(self.roster):
                row = tk.Frame(list_frame, bg="#1a1a20")
                row.pack(fill="x", pady=1)

                var = tk.BooleanVar(value=name in self.included_chars)
                cb = tk.Checkbutton(row, text=name, variable=var, bg="#1a1a20", fg="#fff", selectcolor="#333", activebackground="#1a1a20", activeforeground="#fff")
                cb.var = var
                cb.pack(side="left")
                cb.config(command=lambda n=name, v=var: toggle(n, v))

                tk.Button(row, text="✕", command=lambda n=name: remove(n), bg="#1a1a20", fg="#e05c5c", bd=0).pack(side="right")

        def toggle(n, v):
            if v.get(): self.included_chars.add(n)
            else: self.included_chars.discard(n)
            self._save_config()
            self._last_state_hash = None

        def remove(n):
            self.roster.discard(n)
            self.included_chars.discard(n)
            self._save_config()
            self._last_state_hash = None
            refresh_list()

        refresh_list()

        tk.Label(tw, text=f"Wakfu Damage Meter v{APP_VERSION}", bg="#1a1a20", fg="#555555", font=("Segoe UI", 8)).pack(side="bottom", pady=5)

    def _update_custom_hotkey(self):
        new_hk = self.hotkey_var.get().strip().lower()
        self.hotkey_var.set(new_hk)
        self.hotkey_manager.update_hotkey(new_hk)
        self._save_config()

    def _choose_path(self, parent_win):
        self._modal_dialog_open = True
        try:
            chosen = filedialog.askdirectory(parent=parent_win, initialdir=self.log_path_var.get() or ".")
        finally:
            self._modal_dialog_open = False
        if chosen:
            self.log_path_var.set(chosen)
            self._save_config()
            self.tailer.request_reparse()
        if parent_win and parent_win.winfo_exists():
            parent_win.lift()

    def _on_opacity_change(self, value):
        self._apply_opacity()
        self._save_config()

    def _toggle_clickthrough(self):
        self.clickthrough = not self.clickthrough
        self._last_state_hash = None
        if sys.platform != "win32": return
        try:
            GWL_EXSTYLE = -20
            WS_EX_LAYERED, WS_EX_TRANSPARENT = 0x00080000, 0x00000020
            for window in [self.root, self.bg_window, self.details_root, self.details_bg]:
                hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                if self.clickthrough:
                    style |= WS_EX_LAYERED | WS_EX_TRANSPARENT
                else:
                    style &= ~WS_EX_TRANSPARENT
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception: pass

    def _start_drag_bindings(self):
        self._drag_data = {"x": 0, "y": 0, "dragging": False}

        def on_press(event):
            if event.y < 40:
                self._drag_data["x"] = event.x_root - self.app_x
                self._drag_data["y"] = event.y_root - self.app_y
                self._drag_data["dragging"] = True
            else:
                self._drag_data["dragging"] = False

        def on_drag(event):
            if self._drag_data.get("dragging"):
                self._sync_windows(event.x_root - self._drag_data["x"], event.y_root - self._drag_data["y"])

        self.canvas.bind("<ButtonPress-1>", on_press, add="+")
        self.canvas.bind("<B1-Motion>", on_drag, add="+")
        self.bg_window.bind("<ButtonPress-1>", lambda e: self.root.lift(self.bg_window))
        self.details_bg.bind("<ButtonPress-1>", lambda e: self.details_root.lift(self.details_bg))

    def _quit_app(self):
        self.tailer.stop()
        self._save_config()
        try: keyboard.unhook_all()
        except Exception: pass
        self.root.destroy()
        os._exit(0)

    def run(self):
        self.root.mainloop()

_APP_MUTEX = None

if __name__ == "__main__":
    if sys.platform == "win32":
        _APP_MUTEX = ctypes.windll.kernel32.CreateMutexW(None, False, "WakfuDamageMeter_Mutex_1_6_0_40")
        if ctypes.windll.kernel32.GetLastError() == 183:
            sys.exit(0)
    app = OverlayApp()
    app.run()