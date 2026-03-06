import asyncio
import json
import os
import random
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeDefault, FSInputFile
from aiogram.filters import Command, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN", "8614643355:AAGM2X4p-xTs6KNuEThKMo3hvYG2eFRkesQ")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7877170613"))

# Настройки базы данных
DATABASE_FILE = os.getenv("DATABASE_FILE", "game_database.db")
WAR_IMAGES_FOLDER = "war_images"

# Настройки игры
WAR_COOLDOWN_MINUTES = 2
WAR_PREPARATION_SECONDS = 60
WAR_DURATION_SECONDS = 30

# Создаем папку для изображений войны
if not os.path.exists(WAR_IMAGES_FOLDER):
    os.makedirs(WAR_IMAGES_FOLDER)
    print(f"📁 Создана папка для изображений войны: {WAR_IMAGES_FOLDER}")


@dataclass
class Country:
    name: str
    emoji: str
    base_income: float
    population_bonus: float = 1.0
    army_cost: int = 1000
    city_cost: int = 5000
    war_image: str = "war_default.jpg"


COUNTRIES = {
    "russia": Country("Россия", "🇷🇺", 12.0, population_bonus=1.5, war_image="russia_war.jpg"),
    "ukraine": Country("Украина", "🇺🇦", 9.0, population_bonus=1.2, war_image="ukraine_war.jpg"),
    "belarus": Country("Беларусь", "🇧🇾", 7.0, population_bonus=1.1, war_image="belarus_war.jpg"),
    "poland": Country("Польша", "🇵🇱", 10.0, population_bonus=1.2, war_image="poland_war.jpg"),
    "germany": Country("Германия", "🇩🇪", 15.0, population_bonus=1.4, war_image="germany_war.jpg"),
    "france": Country("Франция", "🇫🇷", 14.0, population_bonus=1.3, war_image="france_war.jpg"),
    "uk": Country("Великобритания", "🇬🇧", 13.0, population_bonus=1.3, war_image="uk_war.jpg"),
    "italy": Country("Италия", "🇮🇹", 12.0, population_bonus=1.2, war_image="italy_war.jpg"),
    "spain": Country("Испания", "🇪🇸", 11.0, population_bonus=1.2, war_image="spain_war.jpg"),
    "sweden": Country("Швеция", "🇸🇪", 10.0, population_bonus=1.1, war_image="sweden_war.jpg"),
    "norway": Country("Норвегия", "🇳🇴", 9.0, population_bonus=1.1, war_image="norway_war.jpg"),
    "finland": Country("Финляндия", "🇫🇮", 8.0, population_bonus=1.0, war_image="finland_war.jpg"),
    "denmark": Country("Дания", "🇩🇰", 8.5, population_bonus=1.0, war_image="denmark_war.jpg"),
    "greece": Country("Греция", "🇬🇷", 8.0, population_bonus=1.0, war_image="greece_war.jpg"),
    "portugal": Country("Португалия", "🇵🇹", 8.0, population_bonus=1.0, war_image="portugal_war.jpg"),
    "croatia": Country("Хорватия", "🇭🇷", 7.0, population_bonus=1.0, war_image="croatia_war.jpg"),
    "serbia": Country("Сербия", "🇷🇸", 7.0, population_bonus=1.0, war_image="serbia_war.jpg"),
    "austria": Country("Австрия", "🇦🇹", 9.0, population_bonus=1.0, war_image="austria_war.jpg"),
    "switzerland": Country("Швейцария", "🇨🇭", 11.0, population_bonus=1.1, war_image="switzerland_war.jpg"),
    "czech": Country("Чехия", "🇨🇿", 8.5, population_bonus=1.0, war_image="czech_war.jpg"),
    "hungary": Country("Венгрия", "🇭🇺", 7.5, population_bonus=1.0, war_image="hungary_war.jpg"),
    "netherlands": Country("Нидерланды", "🇳🇱", 10.0, population_bonus=1.1, war_image="netherlands_war.jpg"),
    "belgium": Country("Бельгия", "🇧🇪", 9.0, population_bonus=1.0, war_image="belgium_war.jpg"),
    "luxembourg": Country("Люксембург", "🇱🇺", 12.0, population_bonus=1.0, war_image="luxembourg_war.jpg"),
    "romania": Country("Румыния", "🇷🇴", 7.0, population_bonus=1.0, war_image="romania_war.jpg"),
    "bulgaria": Country("Болгария", "🇧🇬", 6.5, population_bonus=1.0, war_image="bulgaria_war.jpg"),
    "albania": Country("Албания", "🇦🇱", 6.0, population_bonus=1.0, war_image="albania_war.jpg"),
    "latvia": Country("Латвия", "🇱🇻", 6.5, population_bonus=1.0, war_image="latvia_war.jpg"),
    "lithuania": Country("Литва", "🇱🇹", 6.5, population_bonus=1.0, war_image="lithuania_war.jpg"),
    "estonia": Country("Эстония", "🇪🇪", 6.5, population_bonus=1.0, war_image="estonia_war.jpg"),
    "turkey": Country("Турция", "🇹🇷", 9.5, population_bonus=1.3, war_image="turkey_war.jpg"),
    "ireland": Country("Ирландия", "🇮🇪", 8.5, population_bonus=1.0, war_image="ireland_war.jpg"),
    "iceland": Country("Исландия", "🇮🇸", 7.0, population_bonus=1.0, war_image="iceland_war.jpg"),
    "slovakia": Country("Словакия", "🇸🇰", 7.0, population_bonus=1.0, war_image="slovakia_war.jpg"),
    "slovenia": Country("Словения", "🇸🇮", 7.0, population_bonus=1.0, war_image="slovenia_war.jpg"),
}


@dataclass
class Player:
    user_id: int
    username: str
    country: str
    money: float = 1000.0
    army_level: int = 1
    city_level: int = 1
    population: int = 1000
    last_income: datetime = field(default_factory=datetime.now)
    wins: int = 0
    losses: int = 0


# ========== НОВЫЙ КЛАСС ДЛЯ СИСТЕМЫ СОЮЗНИКОВ ==========

class AllianceSystem:
    """Система союзников и совместных атак"""
    
    def __init__(self):
        self.alliances = defaultdict(dict)  # chat_id -> {user_id: [allies_ids]}
        self.alliance_requests = defaultdict(dict)  # chat_id -> {from_user: to_user}
        self.joint_attacks = {}  # attack_id -> attack data
        self.attack_counter = 0
    
    def send_request(self, chat_id: int, from_user: int, to_user: int):
        """Отправить запрос в союзники"""
        self.alliance_requests[chat_id][from_user] = to_user
    
    def get_request(self, chat_id: int, from_user: int) -> Optional[int]:
        """Получить запрос в союзники"""
        return self.alliance_requests[chat_id].get(from_user)
    
    def remove_request(self, chat_id: int, from_user: int):
        """Удалить запрос в союзники"""
        if from_user in self.alliance_requests[chat_id]:
            del self.alliance_requests[chat_id][from_user]
    
    def accept_request(self, chat_id: int, from_user: int, to_user: int):
        """Принять запрос в союзники"""
        if chat_id not in self.alliances:
            self.alliances[chat_id] = defaultdict(list)
        
        # Добавляем друг друга в союзники
        if to_user not in self.alliances[chat_id][from_user]:
            self.alliances[chat_id][from_user].append(to_user)
        if from_user not in self.alliances[chat_id][to_user]:
            self.alliances[chat_id][to_user].append(from_user)
        
        # Удаляем запрос
        self.remove_request(chat_id, from_user)
    
    def get_allies(self, chat_id: int, user_id: int) -> List[int]:
        """Получить список союзников игрока"""
        return self.alliances.get(chat_id, {}).get(user_id, [])
    
    def break_alliance(self, chat_id: int, user1: int, user2: int):
        """Разорвать союз"""
        if chat_id in self.alliances:
            if user1 in self.alliances[chat_id] and user2 in self.alliances[chat_id][user1]:
                self.alliances[chat_id][user1].remove(user2)
            if user2 in self.alliances[chat_id] and user1 in self.alliances[chat_id][user2]:
                self.alliances[chat_id][user2].remove(user1)
    
    def create_joint_attack(self, attacker_id: int, target_id: int, chat_id: int) -> str:
        """Создать совместную атаку"""
        self.attack_counter += 1
        attack_id = f"attack_{self.attack_counter}_{chat_id}"
        
        self.joint_attacks[attack_id] = {
            "attacker_id": attacker_id,
            "target_id": target_id,
            "chat_id": chat_id,
            "participants": [attacker_id],  # участники атаки
            "start_time": datetime.now()
        }
        
        return attack_id
    
    def join_attack(self, attack_id: str, user_id: int) -> bool:
        """Присоединиться к совместной атаке"""
        if attack_id not in self.joint_attacks:
            return False
        
        attack = self.joint_attacks[attack_id]
        if user_id not in attack["participants"]:
            attack["participants"].append(user_id)
            return True
        return False
    
    def get_attack(self, attack_id: str) -> Optional[Dict]:
        """Получить данные атаки"""
        return self.joint_attacks.get(attack_id)
    
    def remove_attack(self, attack_id: str):
        """Удалить атаку"""
        if attack_id in self.joint_attacks:
            del self.joint_attacks[attack_id]


alliance_system = AllianceSystem()


class WarPreparation:
    def __init__(self, attacker_id: int, defender_id: int, chat_id: int, attack_id: str = None):
        self.attacker_id = attacker_id
        self.defender_id = defender_id
        self.chat_id = chat_id
        self.attack_id = attack_id  # ID совместной атаки если есть
        self.start_time = datetime.now()
        self.help_offers = []
        self.attackers_allies = []
        self.defenders_allies = []
        self.message_id = None


class WarSystem:
    def __init__(self):
        self.preparations = {}

    def start_preparation(self, attacker_id: int, defender_id: int, chat_id: int, attack_id: str = None) -> WarPreparation:
        prep = WarPreparation(attacker_id, defender_id, chat_id, attack_id)
        self.preparations[chat_id] = prep
        return prep

    def get_preparation(self, chat_id: int) -> Optional[WarPreparation]:
        return self.preparations.get(chat_id)

    def add_help(self, chat_id: int, helper_id: int, target_id: int, help_type: str, amount: int):
        prep = self.preparations.get(chat_id)
        if not prep:
            return False
        
        prep.help_offers.append({
            "helper_id": helper_id,
            "target_id": target_id,
            "type": help_type,
            "amount": amount
        })
        
        if target_id == prep.attacker_id:
            if helper_id not in prep.attackers_allies:
                prep.attackers_allies.append(helper_id)
        else:
            if helper_id not in prep.defenders_allies:
                prep.defenders_allies.append(helper_id)
        
        return True

    def end_preparation(self, chat_id: int) -> Optional[WarPreparation]:
        return self.preparations.pop(chat_id, None)

    def is_preparing(self, chat_id: int) -> bool:
        return chat_id in self.preparations


war_system = WarSystem()


class TransferData:
    def __init__(self):
        self.transfers = {}


transfer_data = TransferData()


class WarWarningSystem:
    def __init__(self):
        self.sent_warnings = defaultdict(set)

    async def send_war_warnings(self, chat_id: int):
        try:
            game = await load_game(chat_id)
            if not game or game["war_active"] or not game["last_war"]:
                return

            time_since_last_war = datetime.now() - game["last_war"]
            warning_time = timedelta(minutes=WAR_COOLDOWN_MINUTES - 1)

            if time_since_last_war >= warning_time:
                war_participants = game.get("war_participants", [])
                if len(war_participants) < 2:
                    return

                for player_id in war_participants:
                    if chat_id in self.sent_warnings and player_id in self.sent_warnings[chat_id]:
                        continue

                    try:
                        player = await load_player(player_id, chat_id)
                        if not player:
                            continue

                        remaining_time = timedelta(minutes=WAR_COOLDOWN_MINUTES) - time_since_last_war
                        minutes = int(remaining_time.total_seconds() // 60)
                        seconds = int(remaining_time.total_seconds() % 60)

                        opponent_id = war_participants[0] if player_id == war_participants[1] else war_participants[1]
                        opponent = await load_player(opponent_id, chat_id)
                        opponent_name = opponent.username if opponent else "противник"

                        warning_text = (
                            f"⚠️ **ПРЕДУПРЕЖДЕНИЕ О ВОЙНЕ** ⚔️\n\n"
                            f"Скоро можно будет начать новую войну!\n"
                            f"⏳ Осталось времени: **{minutes}:{seconds:02d}**\n\n"
                            f"📊 Ваш последний противник: {opponent_name}\n"
                            f"👥 Население: {player.population:,}\n"
                            f"💰 Успейте подготовиться и найти союзников!\n\n"
                            f"⚔️ Победитель получит 50% ресурсов и 20% населения проигравшего!"
                        )

                        await bot.send_message(chat_id=player_id, text=warning_text, parse_mode="Markdown")

                        if chat_id not in self.sent_warnings:
                            self.sent_warnings[chat_id] = set()
                        self.sent_warnings[chat_id].add(player_id)

                        await asyncio.sleep(0.3)

                    except Exception as e:
                        print(f"❌ Ошибка отправки предупреждения: {e}")
                        continue

        except Exception as e:
            print(f"❌ Ошибка в системе предупреждений: {e}")


war_warning_system = WarWarningSystem()

# Инициализация бота
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

main_router = Router()
callback_router = Router()
admin_router = Router()


# ========== ФУНКЦИИ БАЗЫ ДАННЫХ ==========

def init_database():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            chat_id INTEGER PRIMARY KEY, 
            creator_id INTEGER, 
            war_active BOOLEAN DEFAULT 0, 
            war_participants TEXT, 
            war_start_time TEXT, 
            last_war TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, 
            username TEXT, 
            country TEXT, 
            money REAL DEFAULT 1000.0, 
            army_level INTEGER DEFAULT 1, 
            city_level INTEGER DEFAULT 1,
            population INTEGER DEFAULT 1000,
            last_income TEXT, 
            wins INTEGER DEFAULT 0, 
            losses INTEGER DEFAULT 0, 
            chat_id INTEGER,
            FOREIGN KEY (chat_id) REFERENCES games (chat_id), 
            UNIQUE(user_id, chat_id)
        )
    ''')

    # Проверяем и добавляем колонку population если её нет
    cursor.execute("PRAGMA table_info(players)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'population' not in columns:
        cursor.execute("ALTER TABLE players ADD COLUMN population INTEGER DEFAULT 1000")
        print("✅ Добавлена колонка population в таблицу players")

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON players(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_chat_id ON players(chat_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_chat ON players(user_id, chat_id)')

    conn.commit()
    conn.close()
    print(f"✅ База данных инициализирована")


async def save_game(chat_id: int, creator_id: int, war_active: bool = False,
                    war_participants: List[int] = None, war_start_time: Optional[datetime] = None,
                    last_war: Optional[datetime] = None):
    await asyncio.get_event_loop().run_in_executor(None, lambda: _save_game_sync(
        chat_id, creator_id, war_active, war_participants, war_start_time, last_war
    ))


def _save_game_sync(chat_id: int, creator_id: int, war_active: bool = False,
                    war_participants: List[int] = None, war_start_time: Optional[datetime] = None,
                    last_war: Optional[datetime] = None):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    war_participants_str = json.dumps(war_participants) if war_participants else "[]"
    war_start_time_str = war_start_time.isoformat() if war_start_time else None
    last_war_str = last_war.isoformat() if last_war else None

    cursor.execute('''
    INSERT OR REPLACE INTO games (chat_id, creator_id, war_active, war_participants, war_start_time, last_war)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (chat_id, creator_id, war_active, war_participants_str, war_start_time_str, last_war_str))

    conn.commit()
    conn.close()


async def save_player(player: Player, chat_id: int):
    await asyncio.get_event_loop().run_in_executor(None, lambda: _save_player_sync(player, chat_id))


def _save_player_sync(player: Player, chat_id: int):
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(players)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'population' in columns:
            cursor.execute('''
            INSERT OR REPLACE INTO players 
            (user_id, username, country, money, army_level, city_level, population, last_income, wins, losses, chat_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                player.user_id, 
                player.username, 
                player.country, 
                player.money,
                player.army_level, 
                player.city_level, 
                player.population,
                player.last_income.isoformat() if player.last_income else datetime.now().isoformat(),
                player.wins, 
                player.losses, 
                chat_id
            ))
        else:
            cursor.execute('''
            INSERT OR REPLACE INTO players 
            (user_id, username, country, money, army_level, city_level, last_income, wins, losses, chat_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                player.user_id, 
                player.username, 
                player.country, 
                player.money,
                player.army_level, 
                player.city_level,
                player.last_income.isoformat() if player.last_income else datetime.now().isoformat(),
                player.wins, 
                player.losses, 
                chat_id
            ))

        conn.commit()
    except Exception as e:
        print(f"❌ Ошибка при сохранении игрока {player.user_id}: {e}")
    finally:
        if conn:
            conn.close()


async def load_game(chat_id: int) -> Optional[Dict]:
    return await asyncio.get_event_loop().run_in_executor(None, lambda: _load_game_sync(chat_id))


def _load_game_sync(chat_id: int) -> Optional[Dict]:
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM games WHERE chat_id = ?', (chat_id,))
        game_data = cursor.fetchone()

        if not game_data:
            return None

        war_start_time = None
        if game_data[4] and isinstance(game_data[4], str):
            try:
                war_start_time = datetime.fromisoformat(game_data[4])
            except (ValueError, TypeError):
                war_start_time = None
                
        last_war = None
        if game_data[5] and isinstance(game_data[5], str):
            try:
                last_war = datetime.fromisoformat(game_data[5])
            except (ValueError, TypeError):
                last_war = None

        return {
            "chat_id": game_data[0],
            "creator_id": game_data[1],
            "war_active": bool(game_data[2]) if game_data[2] else False,
            "war_participants": json.loads(game_data[3]) if game_data[3] and game_data[3] != "[]" else [],
            "war_start_time": war_start_time,
            "last_war": last_war
        }
    except Exception as e:
        print(f"❌ Ошибка при загрузке игры из чата {chat_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


async def load_player(user_id: int, chat_id: int) -> Optional[Player]:
    return await asyncio.get_event_loop().run_in_executor(None, lambda: _load_player_sync(user_id, chat_id))


def _load_player_sync(user_id: int, chat_id: int) -> Optional[Player]:
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(players)")
        columns = [column[1] for column in cursor.fetchall()]
        
        cursor.execute('SELECT * FROM players WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        player_data = cursor.fetchone()
        
        if not player_data:
            return None

        data_dict = {}
        for i, col in enumerate(columns):
            data_dict[col] = player_data[i]
        
        try:
            population_val = data_dict.get('population', 1000)
            if isinstance(population_val, str) and population_val.startswith('202'):
                population = 1000
                cursor.execute("UPDATE players SET population = 1000 WHERE user_id = ? AND chat_id = ?", 
                             (user_id, chat_id))
                conn.commit()
            else:
                population = int(population_val) if population_val is not None else 1000
        except (ValueError, TypeError):
            population = 1000
        
        last_income_str = data_dict.get('last_income')
        try:
            if last_income_str and isinstance(last_income_str, str):
                if 'T' in last_income_str and ('-' in last_income_str or ':' in last_income_str):
                    last_income = datetime.fromisoformat(last_income_str)
                else:
                    last_income = datetime.now()
            else:
                last_income = datetime.now()
        except (ValueError, TypeError):
            last_income = datetime.now()

        return Player(
            user_id=int(data_dict.get('user_id', user_id)),
            username=str(data_dict.get('username', f"User_{user_id}")),
            country=str(data_dict.get('country', 'russia')),
            money=float(data_dict.get('money', 1000.0)),
            army_level=int(data_dict.get('army_level', 1)),
            city_level=int(data_dict.get('city_level', 1)),
            population=population,
            last_income=last_income,
            wins=int(data_dict.get('wins', 0)),
            losses=int(data_dict.get('losses', 0))
        )
    except Exception as e:
        print(f"❌ Ошибка при загрузке игрока {user_id} в чате {chat_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()


async def load_all_players(chat_id: int) -> Dict[int, Player]:
    return await asyncio.get_event_loop().run_in_executor(None, lambda: _load_all_players_sync(chat_id))


def _load_all_players_sync(chat_id: int) -> Dict[int, Player]:
    conn = None
    players = {}
    
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(players)")
        columns = [column[1] for column in cursor.fetchall()]
        
        cursor.execute('SELECT * FROM players WHERE chat_id = ?', (chat_id,))
        players_data = cursor.fetchall()
        
        for player_data in players_data:
            try:
                data_dict = {}
                for i, col in enumerate(columns):
                    data_dict[col] = player_data[i]
                
                try:
                    population_val = data_dict.get('population', 1000)
                    if isinstance(population_val, str) and population_val.startswith('202'):
                        population = 1000
                    else:
                        population = int(population_val) if population_val is not None else 1000
                except (ValueError, TypeError):
                    population = 1000
                
                last_income_str = data_dict.get('last_income')
                try:
                    if last_income_str and isinstance(last_income_str, str):
                        if 'T' in last_income_str and ('-' in last_income_str or ':' in last_income_str):
                            last_income = datetime.fromisoformat(last_income_str)
                        else:
                            last_income = datetime.now()
                    else:
                        last_income = datetime.now()
                except (ValueError, TypeError):
                    last_income = datetime.now()
                
                player = Player(
                    user_id=int(data_dict.get('user_id', 0)),
                    username=str(data_dict.get('username', f"User_{data_dict.get('user_id', 0)}")),
                    country=str(data_dict.get('country', 'russia')),
                    money=float(data_dict.get('money', 1000.0)),
                    army_level=int(data_dict.get('army_level', 1)),
                    city_level=int(data_dict.get('city_level', 1)),
                    population=population,
                    last_income=last_income,
                    wins=int(data_dict.get('wins', 0)),
                    losses=int(data_dict.get('losses', 0))
                )
                players[player.user_id] = player
            except Exception as e:
                print(f"❌ Ошибка при обработке игрока: {e}")
                continue
                
        return players
    except Exception as e:
        print(f"❌ Ошибка при загрузке всех игроков из чата {chat_id}: {e}")
        return {}
    finally:
        if conn:
            conn.close()


async def update_player_income_in_db(user_id: int, chat_id: int) -> float:
    return await asyncio.get_event_loop().run_in_executor(None, lambda: _update_player_income_in_db_sync(user_id, chat_id))


def _update_player_income_in_db_sync(user_id: int, chat_id: int) -> float:
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(players)")
        columns = [column[1] for column in cursor.fetchall()]

        cursor.execute('SELECT * FROM players WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        player_data = cursor.fetchone()

        if not player_data:
            return 0

        data_dict = {}
        for i, col in enumerate(columns):
            data_dict[col] = player_data[i]

        try:
            last_income_str = data_dict.get('last_income')
            if last_income_str and isinstance(last_income_str, str):
                if 'T' in last_income_str and ('-' in last_income_str or ':' in last_income_str):
                    last_income = datetime.fromisoformat(last_income_str)
                else:
                    last_income = datetime.now()
            else:
                last_income = datetime.now()
        except (ValueError, TypeError):
            last_income = datetime.now()

        try:
            population_val = data_dict.get('population', 1000)
            if isinstance(population_val, str) and population_val.startswith('202'):
                population = 1000
            else:
                population = int(population_val) if population_val is not None else 1000
        except (ValueError, TypeError):
            population = 1000

        player = Player(
            user_id=int(data_dict.get('user_id', user_id)),
            username=str(data_dict.get('username', f"User_{user_id}")),
            country=str(data_dict.get('country', 'russia')),
            money=float(data_dict.get('money', 1000.0)),
            army_level=int(data_dict.get('army_level', 1)),
            city_level=int(data_dict.get('city_level', 1)),
            population=population,
            last_income=last_income,
            wins=int(data_dict.get('wins', 0)),
            losses=int(data_dict.get('losses', 0))
        )

        current_time = datetime.now()
        time_diff = (current_time - player.last_income).total_seconds()

        if time_diff > 0:
            country = COUNTRIES.get(player.country)
            if country:
                population_bonus = 1 + (player.population / 10000)
                income = country.base_income * player.city_level * time_diff * population_bonus
                income = round(income, 2)

                if income > 0:
                    player.money += income
                    player.last_income = current_time

                    cursor.execute('''
                    UPDATE players 
                    SET money = ?, last_income = ? 
                    WHERE user_id = ? AND chat_id = ?
                    ''', (player.money, player.last_income.isoformat(), user_id, chat_id))

                    conn.commit()
                    return income
        return 0
        
    except Exception as e:
        print(f"❌ Ошибка обновления дохода для {user_id}: {e}")
        return 0
    finally:
        if conn:
            conn.close()


async def get_all_games() -> Dict[int, Dict]:
    return await asyncio.get_event_loop().run_in_executor(None, lambda: _get_all_games_sync())


def _get_all_games_sync() -> Dict[int, Dict]:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games')
    games_data = cursor.fetchall()
    conn.close()

    games = {}
    for game_data in games_data:
        game = {
            "chat_id": game_data[0],
            "creator_id": game_data[1],
            "war_active": bool(game_data[2]) if game_data[2] else False,
            "war_participants": json.loads(game_data[3]) if game_data[3] and game_data[3] != "[]" else [],
            "war_start_time": datetime.fromisoformat(game_data[4]) if game_data[4] else None,
            "last_war": datetime.fromisoformat(game_data[5]) if game_data[5] else None
        }
        games[game["chat_id"]] = game

    return games


# ========== ФУНКЦИИ КЛАВИАТУР ==========

def get_game_keyboard(player_id: int, chat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data=f"stats_{player_id}_{chat_id}"),
        InlineKeyboardButton(text="🏆 Топ игроков", callback_data=f"top_{player_id}_{chat_id}"),
        width=2
    )
    
    builder.row(
        InlineKeyboardButton(text="⚔️ Улучшить армию", callback_data=f"upgrade_army_{player_id}_{chat_id}"),
        InlineKeyboardButton(text="🏙️ Улучшить город", callback_data=f"upgrade_city_{player_id}_{chat_id}"),
        width=2
    )
    
    builder.row(
        InlineKeyboardButton(text="⚔️ Начать войну", callback_data=f"start_war_{player_id}_{chat_id}"),
        InlineKeyboardButton(text="🔄 Обновить доход", callback_data=f"refresh_{player_id}_{chat_id}"),
        width=2
    )
    
    builder.row(
        InlineKeyboardButton(text="🌍 Сменить страну", callback_data=f"change_country_{player_id}_{chat_id}"),
        InlineKeyboardButton(text="🤝 Союзники", callback_data=f"alliance_menu_{player_id}_{chat_id}"),
        width=2
    )
    
    builder.row(
        InlineKeyboardButton(text="💰 Передать деньги", callback_data=f"transfer_menu_money_{player_id}_{chat_id}"),
        InlineKeyboardButton(text="🎖️ Передать армию", callback_data=f"transfer_menu_army_{player_id}_{chat_id}"),
        width=2
    )
    
    return builder.as_markup()


def get_back_keyboard(player_id: int, chat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_{player_id}_{chat_id}"),
        width=1
    )
    return builder.as_markup()


async def get_players_keyboard(chat_id: int, exclude_id: int, action: str, 
                               current_player_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    players = await load_all_players(chat_id)
    
    sorted_players = sorted(players.values(), key=lambda p: p.username)
    
    for player in sorted_players:
        if player.user_id != exclude_id:
            country = COUNTRIES.get(player.country)
            if country:
                callback_data = f"{action}_{player.user_id}_{current_player_id}_{chat_id}"
                builder.row(
                    InlineKeyboardButton(
                        text=f"{country.emoji} {player.username} (⚔️{player.army_level} 👥{player.population:,})",
                        callback_data=callback_data
                    ),
                    width=1
                )
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{current_player_id}_{chat_id}"),
        width=1
    )
    
    return builder.as_markup()


async def get_war_targets_keyboard(chat_id: int, attacker_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    players = await load_all_players(chat_id)
    
    # Получаем союзников атакующего
    allies = alliance_system.get_allies(chat_id, attacker_id)
    
    sorted_players = sorted(players.values(), key=lambda p: p.army_level, reverse=True)
    
    for player in sorted_players:
        if player.user_id != attacker_id:
            country = COUNTRIES.get(player.country)
            if country:
                # Проверяем, является ли игрок союзником
                is_ally = player.user_id in allies
                ally_icon = "🤝 " if is_ally else ""
                
                power = "💪" * min(player.army_level, 3)
                if player.army_level > 3:
                    power = "💪💪💪+"
                
                builder.row(
                    InlineKeyboardButton(
                        text=f"{ally_icon}{country.emoji} {player.username} ⚔️{player.army_level} {power} 👥{player.population:,}",
                        callback_data=f"wartarget_{player.user_id}_{attacker_id}_{chat_id}"
                    ),
                    width=1
                )
    
    builder.row(
        InlineKeyboardButton(text="⚔️ Совместная атака", callback_data=f"joint_attack_menu_{attacker_id}_{chat_id}"),
        width=1
    )
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{attacker_id}_{chat_id}"),
        width=1
    )
    
    return builder.as_markup()


async def get_joint_attack_keyboard(chat_id: int, attacker_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора цели совместной атаки"""
    builder = InlineKeyboardBuilder()
    players = await load_all_players(chat_id)
    
    # Получаем союзников атакующего
    allies = alliance_system.get_allies(chat_id, attacker_id)
    
    for player in players.values():
        if player.user_id != attacker_id and player.user_id not in allies:
            country = COUNTRIES.get(player.country)
            if country:
                builder.row(
                    InlineKeyboardButton(
                        text=f"{country.emoji} {player.username} (⚔️{player.army_level} 👥{player.population:,})",
                        callback_data=f"joint_target_{player.user_id}_{attacker_id}_{chat_id}"
                    ),
                    width=1
                )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"start_war_{attacker_id}_{chat_id}"),
        width=1
    )
    
    return builder.as_markup()


async def get_allies_keyboard(chat_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для управления союзниками"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🤝 Предложить союз", callback_data=f"alliance_request_{user_id}_{chat_id}"),
        width=1
    )
    
    builder.row(
        InlineKeyboardButton(text="📋 Мои союзники", callback_data=f"alliance_list_{user_id}_{chat_id}"),
        width=1
    )
    
    builder.row(
        InlineKeyboardButton(text="💔 Разорвать союз", callback_data=f"alliance_break_{user_id}_{chat_id}"),
        width=1
    )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"back_{user_id}_{chat_id}"),
        width=1
    )
    
    return builder.as_markup()


def get_countries_keyboard(player_id: int, chat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    countries_list = list(COUNTRIES.items())
    
    for i in range(0, len(countries_list), 2):
        row = countries_list[i:i+2]
        buttons = []
        for country_id, country in row:
            buttons.append(
                InlineKeyboardButton(
                    text=f"{country.emoji} {country.name} (👥+{int(country.population_bonus*100-100)}%)",
                    callback_data=f"country_{country_id}_{player_id}_{chat_id}"
                )
            )
        builder.row(*buttons, width=len(buttons))
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{player_id}_{chat_id}"),
        width=1
    )
    
    return builder.as_markup()


async def get_war_help_keyboard(chat_id: int, prep: WarPreparation, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для помощи в войне"""
    builder = InlineKeyboardBuilder()
    
    attacker = await load_player(prep.attacker_id, chat_id)
    defender = await load_player(prep.defender_id, chat_id)
    
    elapsed = (datetime.now() - prep.start_time).seconds
    remaining = max(0, WAR_PREPARATION_SECONDS - elapsed)
    
    # Получаем союзников
    attacker_allies = alliance_system.get_allies(chat_id, prep.attacker_id)
    defender_allies = alliance_system.get_allies(chat_id, prep.defender_id)
    
    # Кнопки для участников войны
    if user_id == prep.attacker_id:
        builder.row(
            InlineKeyboardButton(text="🆘 Позвать союзников", callback_data=f"war_call_allies_{chat_id}"),
            width=1
        )
        builder.row(
            InlineKeyboardButton(text="📊 Статус", callback_data=f"war_status_{chat_id}"),
            InlineKeyboardButton(text="⏳ Обновить", callback_data=f"war_refresh_{chat_id}"),
            width=2
        )
    elif user_id == prep.defender_id:
        builder.row(
            InlineKeyboardButton(text="🆘 Позвать союзников", callback_data=f"war_call_allies_{chat_id}"),
            width=1
        )
        builder.row(
            InlineKeyboardButton(text="📊 Статус", callback_data=f"war_status_{chat_id}"),
            InlineKeyboardButton(text="⏳ Обновить", callback_data=f"war_refresh_{chat_id}"),
            width=2
        )
    else:
        # Проверяем, является ли игрок союзником
        is_attacker_ally = user_id in attacker_allies
        is_defender_ally = user_id in defender_allies
        
        if is_attacker_ally:
            builder.row(
                InlineKeyboardButton(text="🤝 Помочь союзнику (атака)", callback_data=f"war_help_attacker_{chat_id}"),
                width=1
            )
        elif is_defender_ally:
            builder.row(
                InlineKeyboardButton(text="🤝 Помочь союзнику (защита)", callback_data=f"war_help_defender_{chat_id}"),
                width=1
            )
        else:
            builder.row(
                InlineKeyboardButton(text=f"🤝 Помочь {attacker.username}", callback_data=f"war_help_attacker_{chat_id}"),
                width=1
            )
            builder.row(
                InlineKeyboardButton(text=f"🤝 Помочь {defender.username}", callback_data=f"war_help_defender_{chat_id}"),
                width=1
            )
        
        builder.row(
            InlineKeyboardButton(text="📊 Статус", callback_data=f"war_status_{chat_id}"),
            width=1
        )
    
    builder.row(
        InlineKeyboardButton(text="❌ Выйти", callback_data=f"cancel_{user_id}_{chat_id}"),
        width=1
    )
    
    return builder.as_markup()


# ========== ФУНКЦИИ ДЛЯ СИСТЕМЫ ПРИГЛАШЕНИЙ ==========

class WarInvitationSystem:
    """Система приглашений в войну через личные сообщения"""
    
    def __init__(self):
        self.active_invitations = {}
        self.user_responses = defaultdict(dict)
        self.invitation_timers = {}
    
    def create_invitation(self, chat_id: int, attacker_id: int, defender_id: int, prep_time: int):
        self.active_invitations[chat_id] = {
            "attacker_id": attacker_id,
            "defender_id": defender_id,
            "prep_time": prep_time,
            "start_time": datetime.now(),
            "responses": {
                "for_attacker": [],
                "for_defender": [],
                "neutral": []
            }
        }
    
    def get_invitation(self, chat_id: int) -> Optional[Dict]:
        return self.active_invitations.get(chat_id)
    
    def add_response(self, user_id: int, chat_id: int, side: str):
        invitation = self.active_invitations.get(chat_id)
        if not invitation:
            return False
        
        if side == "attacker":
            if user_id not in invitation["responses"]["for_attacker"]:
                invitation["responses"]["for_attacker"].append(user_id)
        elif side == "defender":
            if user_id not in invitation["responses"]["for_defender"]:
                invitation["responses"]["for_defender"].append(user_id)
        else:
            if user_id not in invitation["responses"]["neutral"]:
                invitation["responses"]["neutral"].append(user_id)
        
        self.user_responses[user_id][chat_id] = side
        return True
    
    def remove_invitation(self, chat_id: int):
        if chat_id in self.active_invitations:
            del self.active_invitations[chat_id]
        if chat_id in self.invitation_timers:
            self.invitation_timers[chat_id].cancel()
            del self.invitation_timers[chat_id]
    
    def get_user_choice(self, user_id: int, chat_id: int) -> Optional[str]:
        return self.user_responses.get(user_id, {}).get(chat_id)


war_invitation_system = WarInvitationSystem()


async def send_war_invitations(chat_id: int, attacker_id: int, defender_id: int, attack_id: str = None):
    """Разослать приглашения всем игрокам в личные сообщения"""
    
    players = await load_all_players(chat_id)
    
    attacker = await load_player(attacker_id, chat_id)
    defender = await load_player(defender_id, chat_id)
    
    if not attacker or not defender:
        return
    
    attacker_country = COUNTRIES.get(attacker.country)
    defender_country = COUNTRIES.get(defender.country)
    
    war_invitation_system.create_invitation(chat_id, attacker_id, defender_id, WAR_PREPARATION_SECONDS)
    
    # Получаем информацию о совместной атаке
    attack_info = ""
    participants = []
    if attack_id:
        attack = alliance_system.get_attack(attack_id)
        if attack:
            participants = attack["participants"]
            attack_info = f"👥 **Совместная атака!** Участников: {len(participants)}\n\n"
    
    for player_id, player in players.items():
        if player_id == attacker_id or player_id == defender_id:
            continue
        
        try:
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(
                    text=f"{attacker_country.emoji if attacker_country else '⚔️'} За {attacker.username}",
                    callback_data=f"war_side_attacker_{chat_id}"
                ),
                width=1
            )
            builder.row(
                InlineKeyboardButton(
                    text=f"{defender_country.emoji if defender_country else '🛡️'} За {defender.username}",
                    callback_data=f"war_side_defender_{chat_id}"
                ),
                width=1
            )
            builder.row(
                InlineKeyboardButton(
                    text="❌ Не участвую",
                    callback_data=f"war_side_neutral_{chat_id}"
                ),
                width=1
            )
            
            invitation_text = (
                f"⚔️ **ПРИГЛАШЕНИЕ НА ВОЙНУ!** ⚔️\n\n"
                f"В чате **{player.username}** начинается война!\n\n"
                f"{attack_info}"
                f"**{attacker_country.emoji if attacker_country else '⚔️'} {attacker.username}**\n"
                f"├─ Атакует\n"
                f"├─ ⚔️ Армия: {attacker.army_level}\n"
                f"└─ 👥 Население: {attacker.population:,}\n\n"
                f"**{defender_country.emoji if defender_country else '🛡️'} {defender.username}**\n"
                f"├─ Защищается\n"
                f"├─ ⚔️ Армия: {defender.army_level}\n"
                f"└─ 👥 Население: {defender.population:,}\n\n"
                f"⏳ Время на подготовку: {WAR_PREPARATION_SECONDS} сек\n\n"
                f"**Выберите сторону:**\n"
                f"• Помощники получат 10% от добычи\n"
                f"• Можно помогать ресурсами\n"
                f"• Ваша поддержка влияет на исход!"
            )
            
            await bot.send_message(
                chat_id=player_id,
                text=invitation_text,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
            
            print(f"📨 Приглашение отправлено игроку {player_id}")
            await asyncio.sleep(0.3)
            
        except Exception as e:
            print(f"❌ Не удалось отправить приглашение игроку {player_id}: {e}")
    
    asyncio.create_task(invitation_timer(chat_id, attacker_id, defender_id, attack_id))


async def invitation_timer(chat_id: int, attacker_id: int, defender_id: int, attack_id: str = None):
    """Таймер сбора ответов на приглашения"""
    await asyncio.sleep(WAR_PREPARATION_SECONDS)
    
    invitation = war_invitation_system.get_invitation(chat_id)
    if not invitation:
        return
    
    for_attacker = len(invitation["responses"]["for_attacker"])
    for_defender = len(invitation["responses"]["for_defender"])
    neutral = len(invitation["responses"]["neutral"])
    total = for_attacker + for_defender + neutral
    
    attacker_player = await load_player(attacker_id, chat_id)
    defender_player = await load_player(defender_id, chat_id)
    
    attacker_country = COUNTRIES.get(attacker_player.country) if attacker_player else None
    defender_country = COUNTRIES.get(defender_player.country) if defender_player else None
    
    attack_info = ""
    if attack_id:
        attack = alliance_system.get_attack(attack_id)
        if attack:
            attack_info = f"👥 **Совместная атака!** Участников: {len(attack['participants'])}\n\n"
    
    results_text = (
        f"📊 **ИТОГИ ПРИГЛАШЕНИЙ**\n\n"
        f"{attack_info}"
        f"Всего опрошено: {total} игроков\n\n"
        f"{attacker_country.emoji if attacker_country else '⚔️'} "
        f"За атакующего: {for_attacker}\n"
        f"{defender_country.emoji if defender_country else '🛡️'} "
        f"За защитника: {for_defender}\n"
        f"❌ Отказались: {neutral}\n\n"
        f"⚔️ Начинаем битву!"
    )
    
    await bot.send_message(chat_id=chat_id, text=results_text, parse_mode="Markdown")
    
    war_invitation_system.remove_invitation(chat_id)


# ========== ФУНКЦИИ ИГРЫ ==========

async def send_war_image(chat_id: int, attacker_country: Country, target_country: Country):
    try:
        attacker_image_path = os.path.join(WAR_IMAGES_FOLDER, attacker_country.war_image)

        if not os.path.exists(attacker_image_path):
            available_images = [f for f in os.listdir(WAR_IMAGES_FOLDER)
                                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))]

            if available_images:
                image_name = random.choice(available_images)
                image_path = os.path.join(WAR_IMAGES_FOLDER, image_name)
            else:
                return
        else:
            image_path = attacker_image_path

        photo = FSInputFile(image_path)
        await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=f"⚔️ {attacker_country.emoji} {attacker_country.name} vs {target_country.emoji} {target_country.name} ⚔️",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"❌ Ошибка при отправке изображения войны: {e}")


async def update_player_menu(message: Message, player: Player, chat_id: int):
    if not chat_id:
        return

    await update_player_income_in_db(player.user_id, chat_id)

    updated_player = await load_player(player.user_id, chat_id)
    if not updated_player:
        return

    country = COUNTRIES.get(updated_player.country)
    if not country:
        return

    income_per_sec = country.base_income * updated_player.city_level * (1 + updated_player.population / 10000)
    army_upgrade_cost = country.army_cost * updated_player.army_level
    city_upgrade_cost = country.city_cost * updated_player.city_level
    
    army_progress_percent = min(100, int((updated_player.money / army_upgrade_cost) * 100)) if army_upgrade_cost > 0 else 0
    city_progress_percent = min(100, int((updated_player.money / city_upgrade_cost) * 100)) if city_upgrade_cost > 0 else 0
    
    army_filled = army_progress_percent // 10
    army_empty = 10 - army_filled
    city_filled = city_progress_percent // 10
    city_empty = 10 - city_filled
    
    army_indicator = "■" * army_filled + "□" * army_empty
    city_indicator = "■" * city_filled + "□" * city_empty
    
    # Получаем список союзников
    allies = alliance_system.get_allies(chat_id, updated_player.user_id)
    allies_count = len(allies)
    allies_names = []
    for ally_id in allies[:3]:  # Показываем первых 3 союзников
        ally = await load_player(ally_id, chat_id)
        if ally:
            allies_names.append(ally.username)
    
    allies_text = f" ({', '.join(allies_names)})" if allies_names else ""
    
    win_rate = (updated_player.wins / (updated_player.wins + updated_player.losses) * 100) if (updated_player.wins + updated_player.losses) > 0 else 0

    text = (
        f"🎮 **ИГРОВОЙ ПРОФИЛЬ** 🎮\n\n"
        f"**{country.emoji} {country.name}**\n"
        f"👤 **Игрок:** {updated_player.username}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Население:** {updated_player.population:,}\n"
        f"💰 **Казна:** {int(updated_player.money):,} монет\n"
        f"📈 **Доход:** {income_per_sec:.1f} монет/сек\n"
        f"🤝 **Союзники:** {allies_count}{allies_text}\n\n"
        f"⚔️ **Армия:** Уровень {updated_player.army_level}\n"
        f"{army_indicator} ({army_progress_percent}%)\n"
        f"💰 След. уровень: {army_upgrade_cost:,} монет\n\n"
        f"🏙️ **Город:** Уровень {updated_player.city_level}\n"
        f"{city_indicator} ({city_progress_percent}%)\n"
        f"💰 След. уровень: {city_upgrade_cost:,} монет\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 Победы: {updated_player.wins} | 💀 Поражения: {updated_player.losses}\n"
        f"📊 Win Rate: {win_rate:.1f}%"
    )

    try:
        await message.edit_text(text, reply_markup=get_game_keyboard(updated_player.user_id, chat_id), 
                               parse_mode="Markdown")
    except TelegramBadRequest:
        await message.answer(text, reply_markup=get_game_keyboard(updated_player.user_id, chat_id), 
                           parse_mode="Markdown")


async def start_war_preparation(attacker_id: int, defender_id: int, chat_id: int, callback_message: Message, attack_id: str = None):
    """Начать подготовку к войне с рассылкой приглашений"""
    
    attacker = await load_player(attacker_id, chat_id)
    defender = await load_player(defender_id, chat_id)
    
    prep = war_system.start_preparation(attacker_id, defender_id, chat_id, attack_id)
    
    # Получаем союзников атакующего
    attacker_allies = alliance_system.get_allies(chat_id, attacker_id)
    
    attack_info = ""
    if attack_id:
        attack = alliance_system.get_attack(attack_id)
        if attack:
            participants = attack["participants"]
            attack_info = f"👥 **Совместная атака!** Участников: {len(participants)}\n\n"
    
    prep_text = (
        f"⚔️ **ПОДГОТОВКА К ВОЙНЕ** ⚔️\n\n"
        f"{attack_info}"
        f"**{attacker.username}** (Союзников: {len(attacker_allies)}) хочет атаковать **{defender.username}**!\n\n"
        f"⏳ Время на подготовку: {WAR_PREPARATION_SECONDS} секунд\n\n"
        f"📨 **ВСЕМ ИГРОКАМ РАЗОСЛАНЫ ПРИГЛАШЕНИЯ В ЛС!**\n\n"
        f"**Что можно делать:**\n"
        f"• Выбрать сторону в личных сообщениях\n"
        f"• Помогать ресурсами через /transfer\n"
        f"• Союзники получат 10% добычи\n\n"
        f"👥 Население влияет на силу в бою!"
    )
    
    msg = await callback_message.edit_text(
        prep_text,
        reply_markup=await get_war_help_keyboard(chat_id, prep, attacker_id),
        parse_mode="Markdown"
    )
    
    prep.message_id = msg.message_id
    
    await send_war_invitations(chat_id, attacker_id, defender_id, attack_id)
    
    asyncio.create_task(war_preparation_timer(chat_id))


async def war_preparation_timer(chat_id: int):
    """Таймер подготовки к войне"""
    for i in range(WAR_PREPARATION_SECONDS, 0, -10):
        await asyncio.sleep(10)
        
        prep = war_system.get_preparation(chat_id)
        if not prep:
            return
        
        await update_war_preparation_status(chat_id)
    
    await start_actual_war(chat_id)


async def update_war_preparation_status(chat_id: int):
    """Обновить статус подготовки"""
    prep = war_system.get_preparation(chat_id)
    if not prep:
        return
    
    attacker = await load_player(prep.attacker_id, chat_id)
    defender = await load_player(prep.defender_id, chat_id)
    
    elapsed = (datetime.now() - prep.start_time).seconds
    remaining = max(0, WAR_PREPARATION_SECONDS - elapsed)
    
    # Получаем союзников
    attacker_allies = alliance_system.get_allies(chat_id, prep.attacker_id)
    defender_allies = alliance_system.get_allies(chat_id, prep.defender_id)
    
    # Получаем помощников из приглашений
    invitation = war_invitation_system.get_invitation(chat_id)
    invited_attackers = len(invitation["responses"]["for_attacker"]) if invitation else 0
    invited_defenders = len(invitation["responses"]["for_defender"]) if invitation else 0
    
    attack_info = ""
    if prep.attack_id:
        attack = alliance_system.get_attack(prep.attack_id)
        if attack:
            attack_info = f"👥 **Совместная атака!** Участников: {len(attack['participants'])}\n\n"
    
    status_text = (
        f"⚔️ **ПОДГОТОВКА К ВОЙНЕ** ⚔️\n\n"
        f"{attack_info}"
        f"⏳ До битвы: {remaining} сек\n\n"
        f"**АТАКУЮЩИЙ:** {attacker.username}\n"
        f"├─ Постоянные союзники: {len(attacker_allies)}\n"
        f"├─ Приглашенные: {invited_attackers}\n"
        f"├─ Всего помощников: {len(attacker_allies) + invited_attackers}\n"
        f"└─ Сила: ⚔️{attacker.army_level} 👥{attacker.population:,}\n\n"
        f"**ЗАЩИТНИК:** {defender.username}\n"
        f"├─ Постоянные союзники: {len(defender_allies)}\n"
        f"├─ Приглашенные: {invited_defenders}\n"
        f"├─ Всего помощников: {len(defender_allies) + invited_defenders}\n"
        f"└─ Сила: ⚔️{defender.army_level} 👥{defender.population:,}\n\n"
    )
    
    if prep.help_offers:
        status_text += "**📦 Помощь:**\n"
        for help_item in prep.help_offers[-3:]:
            helper = await load_player(help_item["helper_id"], chat_id)
            target = await load_player(help_item["target_id"], chat_id)
            if helper and target:
                if help_item["type"] == "money":
                    status_text += f"• {helper.username} дал {help_item['amount']}💰 {target.username}\n"
                else:
                    status_text += f"• {helper.username} дал {help_item['amount']}⚔️ {target.username}\n"
    
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=prep.message_id,
            text=status_text,
            reply_markup=await get_war_help_keyboard(chat_id, prep, prep.attacker_id),
            parse_mode="Markdown"
        )
    except:
        pass


async def get_helpers_list(chat_id: int) -> Dict[str, List[int]]:
    """Получить списки помощников из приглашений и постоянных союзников"""
    helpers = {"attackers": [], "defenders": []}
    
    # Добавляем постоянных союзников
    prep = war_system.get_preparation(chat_id)
    if prep:
        attacker_allies = alliance_system.get_allies(chat_id, prep.attacker_id)
        defender_allies = alliance_system.get_allies(chat_id, prep.defender_id)
        helpers["attackers"].extend(attacker_allies)
        helpers["defenders"].extend(defender_allies)
    
    # Добавляем приглашенных
    invitation = war_invitation_system.get_invitation(chat_id)
    if invitation:
        helpers["attackers"].extend(invitation["responses"]["for_attacker"])
        helpers["defenders"].extend(invitation["responses"]["for_defender"])
    
    # Убираем дубликаты
    helpers["attackers"] = list(set(helpers["attackers"]))
    helpers["defenders"] = list(set(helpers["defenders"]))
    
    return helpers


async def start_actual_war(chat_id: int):
    """Начать реальную войну с учетом союзников и совместных атак"""
    prep = war_system.end_preparation(chat_id)
    if not prep:
        return
    
    helpers = await get_helpers_list(chat_id)
    
    # Добавляем их в подготовку
    for helper_id in helpers["attackers"]:
        if helper_id not in prep.attackers_allies:
            prep.attackers_allies.append(helper_id)
    
    for helper_id in helpers["defenders"]:
        if helper_id not in prep.defenders_allies:
            prep.defenders_allies.append(helper_id)
    
    attacker = await load_player(prep.attacker_id, chat_id)
    defender = await load_player(prep.defender_id, chat_id)
    
    if not attacker or not defender:
        await bot.send_message(chat_id, "❌ Не удалось начать войну: игроки не найдены")
        return
    
    # Применяем помощь
    for help_item in prep.help_offers:
        helper = await load_player(help_item["helper_id"], chat_id)
        if not helper:
            continue
        
        if help_item["type"] == "money":
            if help_item["target_id"] == prep.attacker_id:
                attacker.money += help_item["amount"]
            else:
                defender.money += help_item["amount"]
            helper.money -= help_item["amount"]
        else:
            if help_item["target_id"] == prep.attacker_id:
                attacker.army_level += help_item["amount"]
            else:
                defender.army_level += help_item["amount"]
            helper.army_level -= help_item["amount"]
        
        await save_player(helper, chat_id)
    
    await save_player(attacker, chat_id)
    await save_player(defender, chat_id)
    
    game = await load_game(chat_id)
    war_participants = [attacker.user_id, defender.user_id]
    game["war_active"] = True
    game["war_participants"] = war_participants
    game["war_start_time"] = datetime.now()
    await save_game(chat_id, game["creator_id"], True, war_participants, datetime.now(), game["last_war"])
    
    attacker_country = COUNTRIES.get(attacker.country)
    defender_country = COUNTRIES.get(defender.country)
    
    if attacker_country and defender_country:
        await send_war_image(chat_id, attacker_country, defender_country)
    
    # Расчет силы с учетом союзников и населения
    attacker_power = (attacker.army_level * (1 + len(prep.attackers_allies) * 0.2) * 
                     (1 + attacker.population / 5000) * (1 + random.uniform(-0.1, 0.1)))
    defender_power = (defender.army_level * (1 + len(prep.defenders_allies) * 0.2) * 
                     (1 + defender.population / 5000) * (1 + random.uniform(-0.1, 0.1)))
    
    attack_info = ""
    if prep.attack_id:
        attack = alliance_system.get_attack(prep.attack_id)
        if attack:
            attack_info = f"👥 **Совместная атака!** Участников: {len(attack['participants'])}\n\n"
            alliance_system.remove_attack(prep.attack_id)
    
    war_text = (
        f"⚔️ **ВОЙНА НАЧАЛАСЬ!** ⚔️\n\n"
        f"{attack_info}"
        f"{attacker_country.emoji} **{attacker.username}** (⚔️{attacker.army_level} 👥{attacker.population:,})\n"
        f"├─ Союзников: {len(prep.attackers_allies)}\n"
        f"└─ Сила: {attacker_power:.1f}\n\n"
        f"     **VS**\n\n"
        f"{defender_country.emoji} **{defender.username}** (⚔️{defender.army_level} 👥{defender.population:,})\n"
        f"├─ Союзников: {len(prep.defenders_allies)}\n"
        f"└─ Сила: {defender_power:.1f}\n\n"
        f"⏳ Битва продлится {WAR_DURATION_SECONDS} секунд..."
    )
    
    await bot.send_message(chat_id=chat_id, text=war_text, parse_mode="Markdown")
    
    await asyncio.sleep(WAR_DURATION_SECONDS)
    await end_war(chat_id, prep)


async def end_war(chat_id: int, prep: WarPreparation = None):
    """Завершить войну с учетом союзников"""
    try:
        game = await load_game(chat_id)
        if not game or not game["war_active"]:
            return

        war_participants = game["war_participants"]
        if len(war_participants) != 2:
            game["war_active"] = False
            game["war_participants"] = []
            await save_game(chat_id, game["creator_id"], False, [], None, datetime.now())
            return

        attacker = await load_player(war_participants[0], chat_id)
        defender = await load_player(war_participants[1], chat_id)

        if not attacker or not defender:
            game["war_active"] = False
            game["war_participants"] = []
            await save_game(chat_id, game["creator_id"], False, [], None, datetime.now())
            return

        attacker_power = attacker.army_level * (1 + attacker.population / 5000) * (1 + random.uniform(-0.1, 0.1))
        defender_power = defender.army_level * (1 + defender.population / 5000) * (1 + random.uniform(-0.1, 0.1))

        if prep:
            attacker_power *= (1 + len(prep.attackers_allies) * 0.2)
            defender_power *= (1 + len(prep.defenders_allies) * 0.2)

        if attacker_power > defender_power:
            winner = attacker
            loser = defender
            winner_allies = prep.attackers_allies if prep else []
        else:
            winner = defender
            loser = attacker
            winner_allies = prep.defenders_allies if prep else []

        money_reward = int(loser.money * 0.5)
        army_reward = max(1, int(loser.army_level * 0.3))
        population_reward = int(loser.population * 0.2)

        winner.money += money_reward
        winner.army_level += army_reward
        winner.population += population_reward

        loser.money = max(0, loser.money - money_reward)
        loser.army_level = max(1, loser.army_level - army_reward)
        loser.population = max(500, loser.population - population_reward)

        winner.wins += 1
        loser.losses += 1

        await save_player(winner, chat_id)
        await save_player(loser, chat_id)
        
        allies_reward_text = ""
        for ally_id in winner_allies:
            ally = await load_player(ally_id, chat_id)
            if ally:
                ally_bonus = int(money_reward * 0.1)
                ally.money += ally_bonus
                await save_player(ally, chat_id)
                
                try:
                    await bot.send_message(
                        chat_id=ally_id,
                        text=f"🎁 **ВЫ ПОЛУЧИЛИ НАГРАДУ!**\n\n"
                             f"За помощь в войне вы получили {ally_bonus}💰 монет!",
                        parse_mode="Markdown"
                    )
                except:
                    pass
                
                allies_reward_text += f"• {ally.username} +{ally_bonus}💰\n"

        game["war_active"] = False
        game["war_participants"] = []
        game["last_war"] = datetime.now()
        await save_game(chat_id, game["creator_id"], False, [], None, datetime.now())

        winner_country = COUNTRIES.get(winner.country)
        loser_country = COUNTRIES.get(loser.country)

        result_text = (
            f"⚔️ **ВОЙНА ЗАВЕРШЕНА!** ⚔️\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🏆 **ПОБЕДИТЕЛЬ**\n"
            f"{winner_country.emoji} {winner.username}\n\n"
            f"💰 Добыча: {money_reward:,} монет\n"
            f"🎖️ Трофеи: +{army_reward} уровней\n"
            f"👥 Пленные: +{population_reward:,} населения\n\n"
            f"💀 **ПРОИГРАВШИЙ**\n"
            f"{loser_country.emoji} {loser.username}\n"
            f"├─ Осталось: {int(loser.money):,}💰\n"
            f"├─ Армия: {loser.army_level}⚔️\n"
            f"└─ Население: {loser.population:,}👥\n\n"
        )
        
        if allies_reward_text:
            result_text += f"**🤝 Награды союзникам:**\n{allies_reward_text}\n"
        
        result_text += f"━━━━━━━━━━━━━━━━━━━━\n"
        result_text += f"⏳ Следующая война через {WAR_COOLDOWN_MINUTES} минуты"

        await bot.send_message(chat_id=chat_id, text=result_text, parse_mode="Markdown")
        
        war_invitation_system.remove_invitation(chat_id)
        
    except Exception as e:
        print(f"❌ Ошибка при завершении войны: {e}")
        try:
            game = await load_game(chat_id)
            if game:
                game["war_active"] = False
                game["war_participants"] = []
                await save_game(chat_id, game["creator_id"], False, [], None, datetime.now())
        except:
            pass


async def check_and_send_war_warnings():
    while True:
        try:
            games = await get_all_games()
            for chat_id, game in games.items():
                await war_warning_system.send_war_warnings(chat_id)
            await asyncio.sleep(10)
        except Exception as e:
            print(f"❌ Ошибка в системе предупреждений: {e}")
            await asyncio.sleep(30)


# ========== КОМАНДЫ ==========

@main_router.message(Command("start"))
async def handle_start(message: Message):
    if message.chat.type == "private":
        welcome_text = (
            "🎮 **ДОБРО ПОЖАЛОВАТЬ В ИГРУ!** 🎮\n\n"
            "🌍 **Стратегическая игра про страны Европы**\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "**⚔️ НОВЫЕ ФУНКЦИИ:**\n"
            "• 👥 Население влияет на доход и силу\n"
            "• 🤝 Можно создавать союзы с другими игроками\n"
            "• ⚔️ Совместные атаки с союзниками\n"
            "• 📨 Приглашения в ЛС\n"
            "• 🏆 Союзники получают награды\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📌 **Как начать:**\n"
            "1️⃣ Добавьте бота в групповой чат\n"
            "2️⃣ Напишите /game в группе\n"
            "3️⃣ Выберите страну и играйте!\n\n"
            "❓ /help - подробная помощь"
        )
        await message.answer(welcome_text, parse_mode="Markdown")
        return

    await message.answer("🎮 Для начала игры введите /game")


@main_router.message(Command("help"))
async def handle_help_command(message: Message):
    help_text = (
        "🎮 **ПОМОЩЬ ПО ИГРЕ** 🎮\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**⚡ ОСНОВНЫЕ КОМАНДЫ:**\n"
        "├ /game - Создать или войти в игру\n"
        "├ /join - Присоединиться к игре\n"
        "├ /stats - Показать статистику\n"
        "├ /top - Топ игроков чата\n"
        "├ /war - Начать войну\n"
        "├ /refresh - Обновить доход\n"
        "└ /transfer - Передать ресурсы\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🤝 СИСТЕМА СОЮЗНИКОВ:**\n"
        "• Кнопка 🤝 Союзники в меню\n"
        "• Можно создавать постоянные союзы\n"
        "• Союзники получают бонус в бою\n"
        "• Можно устраивать совместные атаки\n\n"
        "**⚔️ СОВМЕСТНАЯ АТАКА:**\n"
        "• При выборе цели нажмите Совместная атака\n"
        "• Все союзники присоединятся к атаке\n"
        "• Сила умножается на количество союзников\n\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    await message.answer(help_text, parse_mode="Markdown")


@main_router.message(Command("game"))
async def handle_game(message: Message):
    if message.chat.type == "private":
        await message.answer("🎮 Игра доступна только в групповых чатах!")
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    existing_game = await load_game(chat_id)

    if existing_game and existing_game["war_active"]:
        await message.answer("⚔️ Сейчас идет война! Подождите ее окончания.")
        return
        
    if war_system.is_preparing(chat_id):
        await message.answer("⚔️ Сейчас идет подготовка к войне! Подождите.")
        return

    if not existing_game:
        await save_game(chat_id, message.from_user.id)
        await message.answer(
            "🎮 **ИГРА СОЗДАНА!** 🎮\n\n"
            "🌍 Чтобы присоединиться, нажмите /join",
            parse_mode="Markdown"
        )
    else:
        player = await load_player(user_id, chat_id)
        if player:
            await update_player_menu(message, player, chat_id)
            return
        await message.answer("🎮 Игра уже создана! Чтобы присоединиться, нажмите /join")


@main_router.message(Command("join"))
async def handle_join(message: Message):
    if message.chat.type == "private":
        await message.answer("🎮 Игра доступна только в групповых чатах!")
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    game = await load_game(chat_id)
    if not game:
        await message.answer("❌ Игра не создана! Сначала создайте игру с помощью /game")
        return

    if game["war_active"]:
        await message.answer("⚔️ Сейчас идет война! Подождите ее окончания.")
        return
        
    if war_system.is_preparing(chat_id):
        await message.answer("⚔️ Сейчас идет подготовка к войне! Подождите.")
        return

    player = await load_player(user_id, chat_id)
    if player:
        await message.answer("✅ Вы уже в игре!")
        await update_player_menu(message, player, chat_id)
        return

    await message.answer(
        "🌍 **ВЫБЕРИТЕ СТРАНУ** 🌍\n\n"
        "Каждая страна имеет бонус к населению:\n"
        "• 🇷🇺 Россия: +50%\n"
        "• 🇩🇪 Германия: +40%\n"
        "• 🇫🇷 Франция: +30%\n"
        "И другие...\n\n"
        "**Выберите страну ниже:**",
        reply_markup=get_countries_keyboard(user_id, chat_id),
        parse_mode="Markdown"
    )


@main_router.message(Command("stats"))
async def handle_stats_command(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    game = await load_game(chat_id)
    if not game:
        await message.answer("❌ В этом чате нет активной игры! Используйте /game")
        return

    player = await load_player(user_id, chat_id)
    if not player:
        await message.answer("❌ Вы не в игре! Используйте /join")
        return

    await update_player_income_in_db(user_id, chat_id)

    updated_player = await load_player(user_id, chat_id)
    if not updated_player:
        return

    country = COUNTRIES.get(updated_player.country)
    if not country:
        return

    income_per_sec = country.base_income * updated_player.city_level * (1 + updated_player.population / 10000)
    army_upgrade_cost = country.army_cost * updated_player.army_level
    city_upgrade_cost = country.city_cost * updated_player.city_level
    
    army_progress_percent = min(100, int((updated_player.money / army_upgrade_cost) * 100)) if army_upgrade_cost > 0 else 0
    city_progress_percent = min(100, int((updated_player.money / city_upgrade_cost) * 100)) if city_upgrade_cost > 0 else 0
    
    army_filled = army_progress_percent // 10
    army_empty = 10 - army_filled
    city_filled = city_progress_percent // 10
    city_empty = 10 - city_filled
    
    army_indicator = "■" * army_filled + "□" * army_empty
    city_indicator = "■" * city_filled + "□" * city_empty
    
    allies = alliance_system.get_allies(chat_id, updated_player.user_id)
    allies_count = len(allies)
    
    win_rate = (updated_player.wins / (updated_player.wins + updated_player.losses) * 100) if (updated_player.wins + updated_player.losses) > 0 else 0

    text = (
        f"📊 **СТАТИСТИКА** 📊\n\n"
        f"**{country.emoji} {country.name}**\n"
        f"👤 **Игрок:** {updated_player.username}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Население:** {updated_player.population:,}\n"
        f"💰 **Казна:** {int(updated_player.money):,} монет\n"
        f"📈 **Доход:** {income_per_sec:.1f} монет/сек\n"
        f"🤝 **Союзники:** {allies_count}\n\n"
        f"⚔️ **Армия:** Уровень {updated_player.army_level}\n"
        f"{army_indicator} ({army_progress_percent}%)\n"
        f"💰 След. уровень: {army_upgrade_cost:,} монет\n\n"
        f"🏙️ **Город:** Уровень {updated_player.city_level}\n"
        f"{city_indicator} ({city_progress_percent}%)\n"
        f"💰 След. уровень: {city_upgrade_cost:,} монет\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 Победы: {updated_player.wins} | 💀 Поражения: {updated_player.losses}\n"
        f"📊 Win Rate: {win_rate:.1f}%"
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=get_game_keyboard(updated_player.user_id, chat_id))


@main_router.message(Command("top"))
async def handle_top_command(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    game = await load_game(chat_id)
    if not game:
        await message.answer("❌ В этом чате нет активной игры! Используйте /game")
        return

    players = await load_all_players(chat_id)

    if not players or len(players) == 0:
        await message.answer("❌ В игре этого чата нет игроков!")
        return

    for player_id in players.keys():
        await update_player_income_in_db(player_id, chat_id)

    players = await load_all_players(chat_id)
    
    sorted_players = sorted(players.values(), key=lambda p: p.army_level * p.population, reverse=True)

    top_text = f"🏆 **ТОП ИГРОКОВ ЧАТА** 🏆\n\n"
    top_text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, player in enumerate(sorted_players[:10], 1):
        country = COUNTRIES.get(player.country)
        emoji = country.emoji if country else "🏳️"
        medal = medals[i-1] if i <= 3 else f"{i}."
        
        allies = alliance_system.get_allies(chat_id, player.user_id)
        allies_icon = "🤝" if allies else ""
        
        power = player.army_level * player.population / 1000
        
        top_text += f"{medal} {emoji} **{player.username}** {allies_icon}\n"
        top_text += f"   ⚔️{player.army_level} | 👥{player.population:,} | 💪{power:.1f}k\n\n"

    top_text += f"━━━━━━━━━━━━━━━━━━━━"

    await message.answer(top_text, parse_mode="Markdown", reply_markup=get_game_keyboard(user_id, chat_id))


@main_router.message(Command("war"))
async def handle_war_command(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    game = await load_game(chat_id)
    if not game:
        await message.answer("❌ В этом чате нет активной игры! Используйте /game")
        return

    if game["war_active"]:
        await message.answer("⚔️ **Война уже идет!** Подождите ее окончания.")
        return
        
    if war_system.is_preparing(chat_id):
        await message.answer("⚔️ **Сейчас идет подготовка к войне!** Подождите.")
        return

    if game["last_war"]:
        time_since_last_war = datetime.now() - game["last_war"]
        if time_since_last_war < timedelta(minutes=WAR_COOLDOWN_MINUTES):
            remaining = timedelta(minutes=WAR_COOLDOWN_MINUTES) - time_since_last_war
            minutes = int(remaining.total_seconds() // 60)
            seconds = int(remaining.total_seconds() % 60)
            await message.answer(f"⏳ **До следующей войны:** {minutes}:{seconds:02d}")
            return

    player = await load_player(user_id, chat_id)
    if not player:
        await message.answer("❌ Вы не в игре! Используйте /join")
        return

    players = await load_all_players(chat_id)
    if len(players) < 2:
        await message.answer("❌ Недостаточно игроков для войны!")
        return

    allies = alliance_system.get_allies(chat_id, user_id)
    allies_text = f" (Союзников: {len(allies)})" if allies else ""

    await message.answer(
        f"⚔️ **ВЫБЕРИТЕ ЦЕЛЬ ДЛЯ АТАКИ** ⚔️\n\n"
        f"**Ваша сила:** ⚔️{player.army_level} | 👥{player.population:,}{allies_text}\n\n"
        f"⚠️ Победитель получит 50% денег и 20% населения!\n"
        f"🤝 Союзники помогут в бою!",
        reply_markup=await get_war_targets_keyboard(chat_id, user_id),
        parse_mode="Markdown"
    )


@main_router.message(Command("refresh"))
async def handle_refresh_command(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    game = await load_game(chat_id)
    if not game:
        await message.answer("❌ В этом чате нет активной игры! Используйте /game")
        return

    income = await update_player_income_in_db(user_id, chat_id)

    if income > 0:
        await message.answer(f"✅ **Начислено:** {income:.1f} монет!")
    else:
        await message.answer("ℹ️ **Новых начислений нет**")

    player = await load_player(user_id, chat_id)
    if player:
        await update_player_menu(message, player, chat_id)


@main_router.message(Command("transfer"))
async def handle_transfer_command(message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    game = await load_game(chat_id)
    if not game:
        await message.answer("❌ В этом чате нет активной игры! Используйте /game")
        return

    if game["war_active"] or war_system.is_preparing(chat_id):
        await message.answer("⚔️ Нельзя передавать ресурсы во время войны или подготовки!")
        return

    player = await load_player(user_id, chat_id)
    if not player:
        await message.answer("❌ Вы не в игре! Используйте /join")
        return

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Передать деньги", callback_data=f"transfer_menu_money_{user_id}_{chat_id}"),
        width=1
    )
    builder.row(
        InlineKeyboardButton(text="🎖️ Передать армию", callback_data=f"transfer_menu_army_{user_id}_{chat_id}"),
        width=1
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{user_id}_{chat_id}"),
        width=1
    )

    await message.answer(
        f"💸 **ПЕРЕДАЧА РЕСУРСОВ** 💸\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **Ваш баланс:** {int(player.money):,} монет\n"
        f"⚔️ **Уровень армии:** {player.army_level}\n"
        f"👥 **Население:** {player.population:,}\n\n"
        f"**Выберите тип передачи:**",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )


# ========== ОБРАБОТЧИКИ CALLBACK ==========

@callback_router.callback_query(F.data.startswith("country_"))
async def handle_country_selection(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    country_id = data[1]
    user_id = int(data[2])
    chat_id = int(data[3])

    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    if game["war_active"] or war_system.is_preparing(chat_id):
        await callback.answer("❌ Нельзя менять страну во время войны!")
        return

    if country_id not in COUNTRIES:
        await callback.answer("❌ Неверная страна!")
        return

    players = await load_all_players(chat_id)
    for player in players.values():
        if player.country == country_id and player.user_id != user_id:
            await callback.answer("❌ Эта страна уже занята!")
            return

    existing_player = await load_player(user_id, chat_id)
    country = COUNTRIES[country_id]

    if existing_player:
        existing_player.country = country_id
        existing_player.population = int(1000 * country.population_bonus)
        await save_player(existing_player, chat_id)
        await callback.message.edit_text(
            f"✅ **Страна изменена!**\n\n"
            f"🌍 **Новая страна:** {country.emoji} {country.name}\n"
            f"👥 **Бонус населения:** +{int(country.population_bonus*100-100)}%\n"
            f"📈 **Новый доход:** {country.base_income * existing_player.city_level:.1f} монет/сек",
            parse_mode="Markdown"
        )
        await update_player_menu(callback.message, existing_player, chat_id)
    else:
        player = Player(
            user_id=user_id,
            username=callback.from_user.username or callback.from_user.first_name,
            country=country_id,
            population=int(1000 * country.population_bonus),
            last_income=datetime.now()
        )
        await save_player(player, chat_id)
        await callback.message.edit_text(
            f"🎉 **ДОБРО ПОЖАЛОВАТЬ!** 🎉\n\n"
            f"🌍 **Страна:** {country.emoji} {country.name}\n"
            f"💰 **Стартовый капитал:** {int(player.money):,} монет\n"
            f"👥 **Население:** {player.population:,}\n"
            f"⚔️ **Армия:** {player.army_level} уровень\n"
            f"🏙️ **Город:** {player.city_level} уровень\n"
            f"📈 **Доход:** {country.base_income * player.city_level:.1f} монет/сек",
            parse_mode="Markdown"
        )
        await update_player_menu(callback.message, player, chat_id)

    await callback.answer()


@callback_router.callback_query(F.data.startswith("stats_"))
async def handle_stats(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 3:
        await callback.answer("❌ Ошибка!")
        return

    target_player_id = int(data[1])
    chat_id = int(data[2])
    user_id = callback.from_user.id

    if target_player_id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    player = await load_player(user_id, chat_id)
    if not player:
        await callback.answer("❌ Вы не в игре!")
        return

    country = COUNTRIES.get(player.country)
    if not country:
        await callback.answer("❌ Ошибка данных страны!")
        return

    income_per_sec = country.base_income * player.city_level * (1 + player.population / 10000)
    army_upgrade_cost = country.army_cost * player.army_level
    city_upgrade_cost = country.city_cost * player.city_level
    
    army_progress_percent = min(100, int((player.money / army_upgrade_cost) * 100)) if army_upgrade_cost > 0 else 0
    city_progress_percent = min(100, int((player.money / city_upgrade_cost) * 100)) if city_upgrade_cost > 0 else 0
    
    army_filled = army_progress_percent // 10
    army_empty = 10 - army_filled
    city_filled = city_progress_percent // 10
    city_empty = 10 - city_filled
    
    army_indicator = "■" * army_filled + "□" * army_empty
    city_indicator = "■" * city_filled + "□" * city_empty
    
    allies = alliance_system.get_allies(chat_id, player.user_id)
    allies_count = len(allies)
    
    win_rate = (player.wins / (player.wins + player.losses) * 100) if (player.wins + player.losses) > 0 else 0

    text = (
        f"📊 **СТАТИСТИКА** 📊\n\n"
        f"**{country.emoji} {country.name}**\n"
        f"👤 **Игрок:** {player.username}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Население:** {player.population:,}\n"
        f"💰 **Казна:** {int(player.money):,} монет\n"
        f"📈 **Доход:** {income_per_sec:.1f} монет/сек\n"
        f"🤝 **Союзники:** {allies_count}\n\n"
        f"⚔️ **Армия:** Уровень {player.army_level}\n"
        f"{army_indicator} ({army_progress_percent}%)\n"
        f"💰 След. уровень: {army_upgrade_cost:,} монет\n\n"
        f"🏙️ **Город:** Уровень {player.city_level}\n"
        f"{city_indicator} ({city_progress_percent}%)\n"
        f"💰 След. уровень: {city_upgrade_cost:,} монет\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 Победы: {player.wins} | 💀 Поражения: {player.losses}\n"
        f"📊 Win Rate: {win_rate:.1f}%"
    )

    await callback.message.edit_text(text, reply_markup=get_back_keyboard(player.user_id, chat_id), 
                                    parse_mode="Markdown")
    await callback.answer()


@callback_router.callback_query(F.data.startswith("back_"))
async def handle_back(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 3:
        await callback.answer("❌ Ошибка!")
        return

    target_player_id = int(data[1])
    chat_id = int(data[2])
    user_id = callback.from_user.id

    if target_player_id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    player = await load_player(user_id, chat_id)
    if player:
        await update_player_menu(callback.message, player, chat_id)
    await callback.answer()


@callback_router.callback_query(F.data.startswith("upgrade_army_"))
async def handle_upgrade_army(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    target_player_id = int(data[2])
    chat_id = int(data[3])
    user_id = callback.from_user.id

    if target_player_id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    if game["war_active"] or war_system.is_preparing(chat_id):
        await callback.answer("⚔️ Нельзя улучшать армию во время войны или подготовки!")
        return

    await update_player_income_in_db(user_id, chat_id)

    player = await load_player(user_id, chat_id)
    if not player:
        await callback.answer("❌ Вы не в игре!")
        return

    country = COUNTRIES.get(player.country)
    if not country:
        await callback.answer("❌ Ошибка данных страны!")
        return

    upgrade_cost = country.army_cost * player.army_level

    if player.money < upgrade_cost:
        await callback.answer(f"❌ Недостаточно денег! Нужно {upgrade_cost:,}💰")
        return

    player.money -= upgrade_cost
    player.army_level += 1
    await save_player(player, chat_id)

    await callback.answer(f"✅ Армия улучшена до {player.army_level} уровня!")

    updated_player = await load_player(user_id, chat_id)
    if updated_player:
        await update_player_menu(callback.message, updated_player, chat_id)


@callback_router.callback_query(F.data.startswith("upgrade_city_"))
async def handle_upgrade_city(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    target_player_id = int(data[2])
    chat_id = int(data[3])
    user_id = callback.from_user.id

    if target_player_id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    if game["war_active"] or war_system.is_preparing(chat_id):
        await callback.answer("⚔️ Нельзя улучшать город во время войны или подготовки!")
        return

    await update_player_income_in_db(user_id, chat_id)

    player = await load_player(user_id, chat_id)
    if not player:
        await callback.answer("❌ Вы не в игре!")
        return

    country = COUNTRIES.get(player.country)
    if not country:
        await callback.answer("❌ Ошибка данных страны!")
        return

    upgrade_cost = country.city_cost * player.city_level

    if player.money < upgrade_cost:
        await callback.answer(f"❌ Недостаточно денег! Нужно {upgrade_cost:,}💰")
        return

    player.money -= upgrade_cost
    player.city_level += 1
    player.population = int(player.population * 1.1)
    await save_player(player, chat_id)

    await callback.answer(f"✅ Город улучшен до {player.city_level} уровня! 👥 Население выросло до {player.population:,}")

    updated_player = await load_player(user_id, chat_id)
    if updated_player:
        await update_player_menu(callback.message, updated_player, chat_id)


@callback_router.callback_query(F.data.startswith("top_"))
async def handle_top(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 3:
        await callback.answer("❌ Ошибка!")
        return

    target_player_id = int(data[1])
    chat_id = int(data[2])
    user_id = callback.from_user.id

    if target_player_id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    players = await load_all_players(chat_id)
    if not players:
        await callback.answer("❌ В игре этого чата нет игроков!")
        return

    for player_id in players.keys():
        await update_player_income_in_db(player_id, chat_id)

    players = await load_all_players(chat_id)
    sorted_players = sorted(players.values(), key=lambda p: p.army_level * p.population, reverse=True)

    top_text = f"🏆 **ТОП ИГРОКОВ** 🏆\n\n"
    top_text += f"━━━━━━━━━━━━━━━━━━━━\n\n"
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, player in enumerate(sorted_players[:10], 1):
        country = COUNTRIES.get(player.country)
        emoji = country.emoji if country else "🏳️"
        medal = medals[i-1] if i <= 3 else f"{i}."
        
        allies = alliance_system.get_allies(chat_id, player.user_id)
        allies_icon = "🤝" if allies else ""
        
        power = player.army_level * player.population / 1000
        
        top_text += f"{medal} {emoji} **{player.username}** {allies_icon}\n"
        top_text += f"   ⚔️{player.army_level} | 👥{player.population:,} | 💪{power:.1f}k\n\n"

    top_text += f"━━━━━━━━━━━━━━━━━━━━"

    await callback.message.edit_text(top_text, reply_markup=get_back_keyboard(user_id, chat_id), 
                                    parse_mode="Markdown")
    await callback.answer()


# ========== ОБРАБОТЧИКИ ДЛЯ СИСТЕМЫ СОЮЗНИКОВ ==========

@callback_router.callback_query(F.data.startswith("alliance_menu_"))
async def handle_alliance_menu(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    user_id = int(data[2])
    chat_id = int(data[3])

    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    if game["war_active"] or war_system.is_preparing(chat_id):
        await callback.answer("⚔️ Нельзя менять союзы во время войны!")
        return

    await callback.message.edit_text(
        "🤝 **УПРАВЛЕНИЕ СОЮЗНИКАМИ**\n\n"
        "Выберите действие:",
        reply_markup=await get_allies_keyboard(chat_id, user_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("alliance_request_"))
async def handle_alliance_request(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    user_id = int(data[2])
    chat_id = int(data[3])

    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    await callback.message.edit_text(
        "🤝 **ВЫБЕРИТЕ ИГРОКА ДЛЯ СОЮЗА**\n\n"
        "Выберите игрока, которому хотите предложить союз:",
        reply_markup=await get_players_keyboard(chat_id, user_id, "alliance_send", user_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("alliance_send_"))
async def handle_alliance_send(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 5:
        await callback.answer("❌ Ошибка!")
        return

    target_id = int(data[2])
    sender_id = int(data[3])
    chat_id = int(data[4])

    if callback.from_user.id != sender_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    target = await load_player(target_id, chat_id)
    if not target:
        await callback.answer("❌ Игрок не найден!")
        return

    # Отправляем запрос в ЛС
    try:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✅ Принять", callback_data=f"alliance_accept_{sender_id}_{chat_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"alliance_decline_{sender_id}_{chat_id}"),
            width=2
        )

        await bot.send_message(
            chat_id=target_id,
            text=f"🤝 **ЗАПРОС НА СОЮЗ**\n\n"
                 f"Игрок **{callback.from_user.username or callback.from_user.first_name}** предлагает вам союз!\n\n"
                 f"Союзники получают бонус в бою и могут участвовать в совместных атаках.",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        
        alliance_system.send_request(chat_id, sender_id, target_id)
        
        await callback.message.edit_text(
            f"✅ **Запрос отправлен**\n\n"
            f"Игроку {target.username} отправлен запрос на союз.\n\n"
            f"Ожидайте ответа в личных сообщениях.",
            reply_markup=get_back_keyboard(sender_id, chat_id),
            parse_mode="Markdown"
        )
    except Exception as e:
        await callback.answer("❌ Не удалось отправить запрос. Возможно, игрок не начал диалог с ботом.")
        return
    
    await callback.answer()


@callback_router.callback_query(F.data.startswith("alliance_accept_"))
async def handle_alliance_accept(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    requester_id = int(data[2])
    chat_id = int(data[3])
    user_id = callback.from_user.id

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    # Проверяем, есть ли запрос
    requested_to = alliance_system.get_request(chat_id, requester_id)
    if requested_to != user_id:
        await callback.answer("❌ Запрос не найден!")
        return

    # Создаем союз
    alliance_system.accept_request(chat_id, requester_id, user_id)

    requester = await load_player(requester_id, chat_id)
    accepter = await load_player(user_id, chat_id)

    await callback.message.edit_text(
        f"✅ **СОЮЗ СОЗДАН!**\n\n"
        f"Вы и {requester.username if requester else 'игрок'} теперь союзники!\n\n"
        f"🤝 Союзники получают +20% к силе в совместных боях.",
        parse_mode="Markdown"
    )

    # Уведомляем второго игрока
    try:
        await bot.send_message(
            chat_id=requester_id,
            text=f"✅ **СОЮЗ ПРИНЯТ!**\n\n"
                 f"{accepter.username if accepter else 'Игрок'} принял ваш запрос на союз!\n\n"
                 f"🤝 Теперь вы можете атаковать совместно.",
            parse_mode="Markdown"
        )
    except:
        pass

    await callback.answer()


@callback_router.callback_query(F.data.startswith("alliance_decline_"))
async def handle_alliance_decline(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    requester_id = int(data[2])
    chat_id = int(data[3])
    user_id = callback.from_user.id

    alliance_system.remove_request(chat_id, requester_id)

    await callback.message.edit_text(
        f"❌ **ЗАПРОС ОТКЛОНЕН**\n\n"
        f"Вы отклонили предложение о союзе.",
        parse_mode="Markdown"
    )

    # Уведомляем второго игрока
    try:
        await bot.send_message(
            chat_id=requester_id,
            text=f"❌ **СОЮЗ ОТКЛОНЕН**\n\n"
                 f"Ваш запрос на союз был отклонен.",
            parse_mode="Markdown"
        )
    except:
        pass

    await callback.answer()


@callback_router.callback_query(F.data.startswith("alliance_list_"))
async def handle_alliance_list(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    user_id = int(data[2])
    chat_id = int(data[3])

    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    allies = alliance_system.get_allies(chat_id, user_id)
    
    if not allies:
        text = "📋 **У вас пока нет союзников**\n\nИспользуйте 🤝 Союзники в меню, чтобы найти союзников."
    else:
        text = "📋 **ВАШИ СОЮЗНИКИ**\n\n"
        for i, ally_id in enumerate(allies, 1):
            ally = await load_player(ally_id, chat_id)
            if ally:
                country = COUNTRIES.get(ally.country)
                text += f"{i}. {country.emoji if country else '🏳️'} **{ally.username}**\n"
                text += f"   ⚔️{ally.army_level} | 👥{ally.population:,}\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_back_keyboard(user_id, chat_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("alliance_break_"))
async def handle_alliance_break(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    user_id = int(data[2])
    chat_id = int(data[3])

    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    allies = alliance_system.get_allies(chat_id, user_id)
    
    if not allies:
        await callback.answer("❌ У вас нет союзников!")
        return

    builder = InlineKeyboardBuilder()
    for ally_id in allies:
        ally = await load_player(ally_id, chat_id)
        if ally:
            builder.row(
                InlineKeyboardButton(
                    text=f"💔 {ally.username}",
                    callback_data=f"alliance_break_confirm_{ally_id}_{user_id}_{chat_id}"
                ),
                width=1
            )
    
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"alliance_menu_{user_id}_{chat_id}"),
        width=1
    )

    await callback.message.edit_text(
        "💔 **ВЫБЕРИТЕ СОЮЗНИКА ДЛЯ РАЗРЫВА**\n\n"
        "Выберите игрока, с которым хотите разорвать союз:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("alliance_break_confirm_"))
async def handle_alliance_break_confirm(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 6:
        await callback.answer("❌ Ошибка!")
        return

    ally_id = int(data[3])
    user_id = int(data[4])
    chat_id = int(data[5])

    if callback.from_user.id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    alliance_system.break_alliance(chat_id, user_id, ally_id)

    ally = await load_player(ally_id, chat_id)

    await callback.message.edit_text(
        f"💔 **СОЮЗ РАЗОРВАН**\n\n"
        f"Вы разорвали союз с {ally.username if ally else 'игроком'}.",
        reply_markup=get_back_keyboard(user_id, chat_id),
        parse_mode="Markdown"
    )

    # Уведомляем второго игрока
    try:
        await bot.send_message(
            chat_id=ally_id,
            text=f"💔 **СОЮЗ РАЗОРВАН**\n\n"
                 f"{callback.from_user.username or callback.from_user.first_name} разорвал союз с вами.",
            parse_mode="Markdown"
        )
    except:
        pass

    await callback.answer()


# ========== ОБРАБОТЧИКИ ДЛЯ СОВМЕСТНЫХ АТАК ==========

@callback_router.callback_query(F.data.startswith("joint_attack_menu_"))
async def handle_joint_attack_menu(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 5:
        await callback.answer("❌ Ошибка!")
        return

    attacker_id = int(data[3])
    chat_id = int(data[4])

    if callback.from_user.id != attacker_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    if game["war_active"] or war_system.is_preparing(chat_id):
        await callback.answer("⚔️ Нельзя начать войну сейчас!")
        return

    allies = alliance_system.get_allies(chat_id, attacker_id)
    
    if not allies:
        await callback.answer("❌ У вас нет союзников для совместной атаки!")
        return

    await callback.message.edit_text(
        "⚔️ **СОВМЕСТНАЯ АТАКА** ⚔️\n\n"
        f"У вас {len(allies)} союзников. Выберите цель для совместной атаки:\n\n"
        "• Все союзники автоматически присоединятся\n"
        "• Сила умножается на количество участников\n"
        "• Награда делится между участниками",
        reply_markup=await get_joint_attack_keyboard(chat_id, attacker_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("joint_target_"))
async def handle_joint_target(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 5:
        await callback.answer("❌ Ошибка!")
        return

    target_id = int(data[2])
    attacker_id = int(data[3])
    chat_id = int(data[4])

    if callback.from_user.id != attacker_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    if game["war_active"] or war_system.is_preparing(chat_id):
        await callback.answer("⚔️ Нельзя начать войну сейчас!")
        return

    if game["last_war"]:
        time_since_last_war = datetime.now() - game["last_war"]
        if time_since_last_war < timedelta(minutes=WAR_COOLDOWN_MINUTES):
            remaining = timedelta(minutes=WAR_COOLDOWN_MINUTES) - time_since_last_war
            minutes = int(remaining.total_seconds() // 60)
            seconds = int(remaining.total_seconds() % 60)
            await callback.answer(f"⏳ До следующей войны {minutes}:{seconds:02d}")
            return

    attacker = await load_player(attacker_id, chat_id)
    if not attacker:
        await callback.answer("❌ Вы не в игре!")
        return

    target = await load_player(target_id, chat_id)
    if not target:
        await callback.answer("❌ Цель не найдена!")
        return

    # Создаем совместную атаку
    attack_id = alliance_system.create_joint_attack(attacker_id, target_id, chat_id)
    
    # Добавляем всех союзников в атаку
    allies = alliance_system.get_allies(chat_id, attacker_id)
    for ally_id in allies:
        alliance_system.join_attack(attack_id, ally_id)
        
        # Уведомляем союзников
        try:
            await bot.send_message(
                chat_id=ally_id,
                text=f"⚔️ **СОВМЕСТНАЯ АТАКА!**\n\n"
                     f"{attacker.username} начал совместную атаку на {target.username}!\n"
                     f"Вы автоматически присоединились к атаке как союзник.\n\n"
                     f"⏳ Подготовка {WAR_PREPARATION_SECONDS} секунд...",
                parse_mode="Markdown"
            )
        except:
            pass

    await start_war_preparation(attacker_id, target_id, chat_id, callback.message, attack_id)


@callback_router.callback_query(F.data.startswith("start_war_"))
async def handle_start_war(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    target_player_id = int(data[2])
    chat_id = int(data[3])
    user_id = callback.from_user.id

    if target_player_id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    if game["war_active"]:
        await callback.answer("⚔️ Война уже идет!")
        return
        
    if war_system.is_preparing(chat_id):
        await callback.answer("⚔️ Сейчас идет подготовка к войне!")
        return

    if game["last_war"]:
        time_since_last_war = datetime.now() - game["last_war"]
        if time_since_last_war < timedelta(minutes=WAR_COOLDOWN_MINUTES):
            remaining = timedelta(minutes=WAR_COOLDOWN_MINUTES) - time_since_last_war
            minutes = int(remaining.total_seconds() // 60)
            seconds = int(remaining.total_seconds() % 60)
            await callback.answer(f"⏳ До следующей войны {minutes}:{seconds:02d}")
            return

    player = await load_player(user_id, chat_id)
    if not player:
        await callback.answer("❌ Вы не в игре!")
        return

    players = await load_all_players(chat_id)
    if len(players) < 2:
        await callback.answer("❌ Недостаточно игроков для войны!")
        return

    allies = alliance_system.get_allies(chat_id, user_id)
    allies_text = f" (Союзников: {len(allies)})" if allies else ""

    await callback.message.edit_text(
        f"⚔️ **ВЫБЕРИТЕ ЦЕЛЬ ДЛЯ АТАКИ** ⚔️\n\n"
        f"**Ваша сила:** ⚔️{player.army_level} | 👥{player.population:,}{allies_text}\n\n"
        f"⚠️ Победитель получит 50% денег и 20% населения!\n"
        f"🤝 Союзники помогут в бою!",
        reply_markup=await get_war_targets_keyboard(chat_id, user_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("wartarget_"))
async def handle_war_target(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    target_player_id = int(data[1])
    attacker_id = int(data[2])
    chat_id = int(data[3])
    user_id = callback.from_user.id

    if attacker_id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    if game["war_active"]:
        await callback.answer("⚔️ Война уже идет!")
        return
        
    if war_system.is_preparing(chat_id):
        await callback.answer("⚔️ Сейчас идет подготовка к войне!")
        return

    attacker = await load_player(attacker_id, chat_id)
    if not attacker:
        await callback.answer("❌ Вы не в игре!")
        return

    target = await load_player(target_player_id, chat_id)
    if not target:
        await callback.answer("❌ Цель не найдена!")
        return

    await start_war_preparation(attacker_id, target_player_id, chat_id, callback.message)


# ========== ОБРАБОТЧИКИ ДЛЯ ПРИГЛАШЕНИЙ ==========

@callback_router.callback_query(F.data.startswith("war_side_"))
async def handle_war_side_choice(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return
    
    side = data[2]
    chat_id = int(data[3])
    user_id = callback.from_user.id
    
    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return
    
    if not game["war_active"] and not war_system.is_preparing(chat_id):
        await callback.answer("❌ Война уже закончилась!")
        return
    
    war_invitation_system.add_response(user_id, chat_id, side)
    
    if side == "attacker":
        text = "✅ Вы присоединились к **атакующему**! Используйте /transfer чтобы помочь ресурсами."
        await callback.answer("✅ Вы за атакующего!")
    elif side == "defender":
        text = "✅ Вы присоединились к **защитнику**! Используйте /transfer чтобы помочь ресурсами."
        await callback.answer("✅ Вы за защитника!")
    else:
        text = "❌ Вы отказались от участия в войне."
        await callback.answer("❌ Вы не участвуете")
    
    await callback.message.edit_text(
        f"⚔️ **ВАШ ВЫБОР**\n\n{text}",
        parse_mode="Markdown"
    )


# ========== ОБРАБОТЧИКИ ДЛЯ ПОМОЩИ В ВОЙНЕ ==========

@callback_router.callback_query(F.data.startswith("war_status_"))
async def handle_war_status(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[2])
    await update_war_preparation_status(chat_id)
    await callback.answer()


@callback_router.callback_query(F.data.startswith("war_refresh_"))
async def handle_war_refresh(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[2])
    await update_war_preparation_status(chat_id)
    await callback.answer()


@callback_router.callback_query(F.data.startswith("war_call_allies_"))
async def handle_war_call_allies(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[3])
    prep = war_system.get_preparation(chat_id)
    if not prep:
        await callback.answer("❌ Подготовка не найдена!")
        return
    
    await callback.message.edit_text(
        "🆘 **ПРИЗЫВ СОЮЗНИКОВ** 🆘\n\n"
        "Напишите в чат сообщение, чтобы позвать союзников!\n\n"
        "Пример: @all 🤝 Нужна помощь в войне!",
        reply_markup=get_back_keyboard(callback.from_user.id, chat_id)
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("war_help_attacker_"))
async def handle_war_help_attacker(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[3])
    prep = war_system.get_preparation(chat_id)
    if not prep:
        await callback.answer("❌ Подготовка не найдена!")
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Помочь деньгами", callback_data=f"war_help_money_attacker_{chat_id}"),
        width=1
    )
    builder.row(
        InlineKeyboardButton(text="🎖️ Помочь армией", callback_data=f"war_help_army_attacker_{chat_id}"),
        width=1
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"war_status_{chat_id}"),
        width=1
    )
    
    await callback.message.edit_text(
        "🤝 **ПОМОЩЬ АТАКУЮЩЕМУ**\n\n"
        "Выберите тип помощи:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("war_help_defender_"))
async def handle_war_help_defender(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[3])
    prep = war_system.get_preparation(chat_id)
    if not prep:
        await callback.answer("❌ Подготовка не найдена!")
        return
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💰 Помочь деньгами", callback_data=f"war_help_money_defender_{chat_id}"),
        width=1
    )
    builder.row(
        InlineKeyboardButton(text="🎖️ Помочь армией", callback_data=f"war_help_army_defender_{chat_id}"),
        width=1
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"war_status_{chat_id}"),
        width=1
    )
    
    await callback.message.edit_text(
        "🤝 **ПОМОЩЬ ЗАЩИТНИКУ**\n\n"
        "Выберите тип помощи:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("war_help_money_attacker_"))
async def handle_war_help_money_attacker(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[4])
    prep = war_system.get_preparation(chat_id)
    if not prep:
        await callback.answer("❌ Подготовка не найдена!")
        return
    
    helper = await load_player(callback.from_user.id, chat_id)
    if not helper:
        await callback.answer("❌ Вы не в игре!")
        return
    
    transfer_data.transfers[callback.from_user.id] = {
        "target_id": prep.attacker_id,
        "type": "money",
        "chat_id": chat_id,
        "war_prep": True
    }
    
    await callback.message.edit_text(
        f"💰 **ПОМОЩЬ ДЕНЬГАМИ**\n\n"
        f"Ваш баланс: {int(helper.money):,} монет\n\n"
        f"Введите сумму для передачи:",
        reply_markup=get_back_keyboard(callback.from_user.id, chat_id)
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("war_help_army_attacker_"))
async def handle_war_help_army_attacker(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[4])
    prep = war_system.get_preparation(chat_id)
    if not prep:
        await callback.answer("❌ Подготовка не найдена!")
        return
    
    helper = await load_player(callback.from_user.id, chat_id)
    if not helper:
        await callback.answer("❌ Вы не в игре!")
        return
    
    if helper.army_level <= 1:
        await callback.answer("❌ У вас минимальный уровень армии!")
        return
    
    transfer_data.transfers[callback.from_user.id] = {
        "target_id": prep.attacker_id,
        "type": "army",
        "chat_id": chat_id,
        "war_prep": True
    }
    
    max_transfer = helper.army_level - 1
    
    await callback.message.edit_text(
        f"🎖️ **ПОМОЩЬ АРМИЕЙ**\n\n"
        f"Ваша армия: {helper.army_level} уровень\n"
        f"Максимум: {max_transfer} уровней\n\n"
        f"Введите количество уровней (1-{max_transfer}):",
        reply_markup=get_back_keyboard(callback.from_user.id, chat_id)
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("war_help_money_defender_"))
async def handle_war_help_money_defender(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[4])
    prep = war_system.get_preparation(chat_id)
    if not prep:
        await callback.answer("❌ Подготовка не найдена!")
        return
    
    helper = await load_player(callback.from_user.id, chat_id)
    if not helper:
        await callback.answer("❌ Вы не в игре!")
        return
    
    transfer_data.transfers[callback.from_user.id] = {
        "target_id": prep.defender_id,
        "type": "money",
        "chat_id": chat_id,
        "war_prep": True
    }
    
    await callback.message.edit_text(
        f"💰 **ПОМОЩЬ ДЕНЬГАМИ**\n\n"
        f"Ваш баланс: {int(helper.money):,} монет\n\n"
        f"Введите сумму для передачи:",
        reply_markup=get_back_keyboard(callback.from_user.id, chat_id)
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("war_help_army_defender_"))
async def handle_war_help_army_defender(callback: CallbackQuery):
    chat_id = int(callback.data.split('_')[4])
    prep = war_system.get_preparation(chat_id)
    if not prep:
        await callback.answer("❌ Подготовка не найдена!")
        return
    
    helper = await load_player(callback.from_user.id, chat_id)
    if not helper:
        await callback.answer("❌ Вы не в игре!")
        return
    
    if helper.army_level <= 1:
        await callback.answer("❌ У вас минимальный уровень армии!")
        return
    
    transfer_data.transfers[callback.from_user.id] = {
        "target_id": prep.defender_id,
        "type": "army",
        "chat_id": chat_id,
        "war_prep": True
    }
    
    max_transfer = helper.army_level - 1
    
    await callback.message.edit_text(
        f"🎖️ **ПОМОЩЬ АРМИЕЙ**\n\n"
        f"Ваша армия: {helper.army_level} уровень\n"
        f"Максимум: {max_transfer} уровней\n\n"
        f"Введите количество уровней (1-{max_transfer}):",
        reply_markup=get_back_keyboard(callback.from_user.id, chat_id)
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("refresh_"))
async def handle_refresh(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 3:
        await callback.answer("❌ Ошибка!")
        return

    target_player_id = int(data[1])
    chat_id = int(data[2])
    user_id = callback.from_user.id

    if target_player_id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    income = await update_player_income_in_db(user_id, chat_id)

    if income > 0:
        await callback.answer(f"✅ Начислено {income:.1f} монет!")
    else:
        await callback.answer("ℹ️ Новых начислений нет")

    player = await load_player(user_id, chat_id)
    if player:
        await update_player_menu(callback.message, player, chat_id)


@callback_router.callback_query(F.data.startswith("change_country_"))
async def handle_change_country(callback: CallbackQuery):
    data = callback.data.split('_')
    if len(data) != 4:
        await callback.answer("❌ Ошибка!")
        return

    target_player_id = int(data[2])
    chat_id = int(data[3])
    user_id = callback.from_user.id

    if target_player_id != user_id:
        await callback.answer("❌ Это не ваша кнопка!")
        return

    game = await load_game(chat_id)
    if not game:
        await callback.answer("❌ Игра не найдена!")
        return

    if game["war_active"] or war_system.is_preparing(chat_id):
        await callback.answer("⚔️ Нельзя менять страну во время войны или подготовки!")
        return

    await callback.message.edit_text(
        "🌍 **ВЫБЕРИТЕ НОВУЮ СТРАНУ** 🌍",
        reply_markup=get_countries_keyboard(user_id, chat_id),
        parse_mode="Markdown"
    )
    await callback.answer()


@callback_router.callback_query(F.data.startswith("transfer_menu_"))
async def handle_transfer_menu(callback: CallbackQuery):
    try:
        parts = callback.data.split('_')
        if len(parts) != 5:
            await callback.answer("❌ Ошибка формата данных!")
            return

        transfer_type = parts[2]
        user_id = int(parts[3])
        chat_id = int(parts[4])

        if callback.from_user.id != user_id:
            await callback.answer("❌ Это не ваша кнопка!")
            return

        game = await load_game(chat_id)
        if not game:
            await callback.answer("❌ Игра не найдена!")
            return

        if game["war_active"] or war_system.is_preparing(chat_id):
            await callback.answer("⚔️ Нельзя передавать ресурсы во время войны или подготовки!")
            return

        await update_player_income_in_db(user_id, chat_id)

        player = await load_player(user_id, chat_id)
        if not player:
            await callback.answer("❌ Вы не в игре!")
            return

        if transfer_type == "money":
            text = f"💸 **ПЕРЕДАЧА ДЕНЕГ** 💸\n\n💰 **Ваш баланс:** {int(player.money):,} монет\n\n**Выберите получателя:**"
        else:
            text = f"🎖️ **ПЕРЕДАЧА АРМИИ** 🎖️\n\n⚔️ **Ваша армия:** {player.army_level} уровень\n\n**Выберите получателя:**"

        await callback.message.edit_text(
            text,
            reply_markup=await get_players_keyboard(chat_id, user_id, f"transfer_{transfer_type}", user_id),
            parse_mode="Markdown"
        )
        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в transfer_menu: {e}")
        await callback.answer("❌ Произошла ошибка!")


@callback_router.callback_query(F.data.startswith("transfer_money_"))
async def handle_transfer_money_target(callback: CallbackQuery):
    try:
        parts = callback.data.split('_')
        if len(parts) != 5:
            await callback.answer("❌ Ошибка формата данных!")
            return

        target_id = int(parts[2])
        sender_id = int(parts[3])
        chat_id = int(parts[4])

        if callback.from_user.id != sender_id:
            await callback.answer("❌ Это не ваша кнопка!")
            return

        game = await load_game(chat_id)
        if not game:
            await callback.answer("❌ Игра не найдена!")
            return

        if game["war_active"] or war_system.is_preparing(chat_id):
            await callback.answer("⚔️ Нельзя передавать ресурсы во время войны или подготовки!")
            return

        sender = await load_player(sender_id, chat_id)
        if not sender:
            await callback.answer("❌ Вы не в игре!")
            return

        receiver = await load_player(target_id, chat_id)
        if not receiver:
            await callback.answer("❌ Получатель не найден!")
            return

        transfer_data.transfers[sender_id] = {
            "target_id": target_id,
            "type": "money",
            "chat_id": chat_id,
            "war_prep": False
        }

        max_amount = int(sender.money)
        await callback.message.edit_text(
            f"💸 **ПЕРЕДАЧА ДЕНЕГ** 💸\n\n"
            f"👤 **Получатель:** {receiver.username}\n"
            f"💰 **Ваш баланс:** {max_amount:,} монет\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✏️ **Введите сумму** (целое число, макс. {max_amount}):",
            parse_mode="Markdown"
        )
        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в transfer_money: {e}")
        await callback.answer("❌ Произошла ошибка!")


@callback_router.callback_query(F.data.startswith("transfer_army_"))
async def handle_transfer_army_target(callback: CallbackQuery):
    try:
        parts = callback.data.split('_')
        if len(parts) != 5:
            await callback.answer("❌ Ошибка формата данных!")
            return

        target_id = int(parts[2])
        sender_id = int(parts[3])
        chat_id = int(parts[4])

        if callback.from_user.id != sender_id:
            await callback.answer("❌ Это не ваша кнопка!")
            return

        game = await load_game(chat_id)
        if not game:
            await callback.answer("❌ Игра не найдена!")
            return

        if game["war_active"] or war_system.is_preparing(chat_id):
            await callback.answer("⚔️ Нельзя передавать ресурсы во время войны или подготовки!")
            return

        sender = await load_player(sender_id, chat_id)
        if not sender:
            await callback.answer("❌ Вы не в игре!")
            return

        receiver = await load_player(target_id, chat_id)
        if not receiver:
            await callback.answer("❌ Получатель не найден!")
            return

        if sender.army_level <= 1:
            await callback.answer("❌ У вас минимальный уровень армии!")
            return

        max_transfer = sender.army_level - 1

        transfer_data.transfers[sender_id] = {
            "target_id": target_id,
            "type": "army",
            "chat_id": chat_id,
            "war_prep": False
        }

        await callback.message.edit_text(
            f"🎖️ **ПЕРЕДАЧА АРМИИ** 🎖️\n\n"
            f"👤 **Получатель:** {receiver.username}\n"
            f"⚔️ **Ваша армия:** {sender.army_level} уровень\n"
            f"📊 **Максимум:** {max_transfer} уровней\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✏️ **Введите количество** (1-{max_transfer}):",
            parse_mode="Markdown"
        )
        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в transfer_army: {e}")
        await callback.answer("❌ Произошла ошибка!")


@main_router.message(lambda message: message.from_user.id in transfer_data.transfers)
async def handle_transfer_amount(message: Message):
    user_id = message.from_user.id

    if user_id not in transfer_data.transfers:
        return

    transfer_info = transfer_data.transfers[user_id]
    target_id = transfer_info["target_id"]
    transfer_type = transfer_info["type"]
    chat_id = transfer_info["chat_id"]
    war_prep = transfer_info.get("war_prep", False)

    try:
        amount = int(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительным числом!")
            return
    except ValueError:
        await message.answer("❌ Пожалуйста, введите целое число!")
        return

    sender = await load_player(user_id, chat_id)
    if not sender:
        await message.answer("❌ Вы не в игре!")
        del transfer_data.transfers[user_id]
        return

    receiver = await load_player(target_id, chat_id)
    if not receiver:
        await message.answer("❌ Получатель не найден!")
        del transfer_data.transfers[user_id]
        return

    if transfer_type == "money":
        if sender.money < amount:
            await message.answer(f"❌ Недостаточно денег! У вас {int(sender.money):,}💰")
            del transfer_data.transfers[user_id]
            return

        if war_prep:
            war_system.add_help(chat_id, user_id, target_id, "money", amount)
            await message.answer(
                f"✅ **Помощь принята!**\n\n"
                f"💰 Вы передали {amount:,} монет\n"
                f"👤 Получатель: {receiver.username}\n\n"
                f"⚔️ Помощь будет учтена в битве!"
            )
            await update_war_preparation_status(chat_id)
        else:
            sender.money -= amount
            receiver.money += amount

            await save_player(sender, chat_id)
            await save_player(receiver, chat_id)

            await message.answer(
                f"✅ **Перевод выполнен!**\n\n"
                f"💰 **Сумма:** {amount:,} монет\n"
                f"👤 **Получатель:** {receiver.username}\n"
                f"💳 **Ваш баланс:** {int(sender.money):,} монет",
                parse_mode="Markdown"
            )

            try:
                await bot.send_message(
                    chat_id=target_id,
                    text=f"💰 **Получен перевод!**\n\n"
                         f"👤 **От:** {sender.username}\n"
                         f"💰 **Сумма:** {amount:,} монет\n"
                         f"💳 **Ваш баланс:** {int(receiver.money):,} монет",
                    parse_mode="Markdown"
                )
            except:
                pass

    elif transfer_type == "army":
        if sender.army_level <= 1:
            await message.answer("❌ У вас минимальный уровень армии!")
            del transfer_data.transfers[user_id]
            return

        if amount >= sender.army_level:
            await message.answer(f"❌ Максимум {sender.army_level - 1} уровней!")
            del transfer_data.transfers[user_id]
            return

        if war_prep:
            war_system.add_help(chat_id, user_id, target_id, "army", amount)
            await message.answer(
                f"✅ **Помощь принята!**\n\n"
                f"🎖️ Вы передали {amount} уровней армии\n"
                f"👤 Получатель: {receiver.username}\n\n"
                f"⚔️ Помощь будет учтена в битве!"
            )
            await update_war_preparation_status(chat_id)
        else:
            sender.army_level -= amount
            receiver.army_level += amount

            await save_player(sender, chat_id)
            await save_player(receiver, chat_id)

            await message.answer(
                f"✅ **Передача армии выполнена!**\n\n"
                f"🎖️ **Передано:** {amount} уровней\n"
                f"👤 **Получатель:** {receiver.username}\n"
                f"⚔️ **Ваша армия:** {sender.army_level} уровень",
                parse_mode="Markdown"
            )

            try:
                await bot.send_message(
                    chat_id=target_id,
                    text=f"🎖️ **Получено подкрепление!**\n\n"
                         f"👤 **От:** {sender.username}\n"
                         f"🎖️ **Получено:** {amount} уровней армии\n"
                         f"⚔️ **Ваша армия:** {receiver.army_level} уровень",
                    parse_mode="Markdown"
                )
            except:
                pass

    del transfer_data.transfers[user_id]

    if not war_prep:
        updated_sender = await load_player(user_id, chat_id)
        if updated_sender:
            await update_player_menu(message, updated_sender, chat_id)


@callback_router.callback_query(F.data.startswith("cancel_"))
async def handle_cancel(callback: CallbackQuery):
    try:
        data = callback.data.split('_')
        if len(data) != 3:
            await callback.answer("❌ Ошибка!")
            return

        user_id = int(data[1])
        chat_id = int(data[2])

        if callback.from_user.id != user_id:
            await callback.answer("❌ Это не ваша кнопка!")
            return

        if user_id in transfer_data.transfers:
            del transfer_data.transfers[user_id]

        game = await load_game(chat_id)
        if game:
            player = await load_player(user_id, chat_id)
            if player:
                await update_player_menu(callback.message, player, chat_id)
                await callback.answer("❌ Действие отменено")
                return

        await callback.message.edit_text(
            "❌ **Действие отменено**\n\n"
            "Используйте /join чтобы присоединиться к игре.",
            parse_mode="Markdown"
        )
        await callback.answer("❌ Действие отменено")

    except Exception as e:
        print(f"❌ Ошибка при обработке отмены: {e}")
        await callback.answer("❌ Ошибка при отмене действия")


# ========== АДМИН КОМАНДЫ ==========

@admin_router.message(Command("force_update"))
async def handle_admin_force_update(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора!")
        return

    await message.answer("🔄 **Запускаю принудительное обновление доходов...**", parse_mode="Markdown")
    await force_update_all_incomes()
    await message.answer("✅ **Доходы успешно обновлены во всех чатах!**", parse_mode="Markdown")


async def admin_add_money(user_id: int, amount: float, chat_id: int = None) -> Tuple[bool, str]:
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: _admin_add_money_sync(user_id, amount, chat_id)
    )


def _admin_add_money_sync(user_id: int, amount: float, chat_id: int = None) -> Tuple[bool, str]:
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        if chat_id:
            cursor.execute('SELECT * FROM players WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
            player_data = cursor.fetchone()

            if not player_data:
                conn.close()
                return False, f"❌ Пользователь с ID {user_id} не найден в чате {chat_id}!"

            current_money = player_data[4]
            new_money = current_money + amount

            cursor.execute('''
            UPDATE players 
            SET money = ? 
            WHERE user_id = ? AND chat_id = ?
            ''', (new_money, user_id, chat_id))

            conn.commit()
            conn.close()
            return True, f"✅ Игроку {user_id} выдано {int(amount)}💰 в чате {chat_id}!\n💰 Новый баланс: {int(new_money)} монет"
        else:
            cursor.execute('SELECT DISTINCT chat_id FROM players WHERE user_id = ?', (user_id,))
            games = cursor.fetchall()

            if not games:
                conn.close()
                return False, f"❌ Пользователь с ID {user_id} не найден в активных играх!"

            total_added = 0
            updated_chats = []

            for game in games:
                chat_id = game[0]
                cursor.execute('SELECT * FROM players WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
                player_data = cursor.fetchone()

                if player_data:
                    current_money = player_data[4]
                    new_money = current_money + amount
                    total_added += amount
                    updated_chats.append(chat_id)

                    cursor.execute('''
                    UPDATE players 
                    SET money = ? 
                    WHERE user_id = ? AND chat_id = ?
                    ''', (new_money, user_id, chat_id))

            conn.commit()
            conn.close()

            if total_added > 0:
                return True, f"✅ Игроку {user_id} выдано {int(amount)}💰 в {len(updated_chats)} играх!\n💰 Всего выдано: {int(total_added)} монет"
            else:
                return False, f"❌ Не удалось выдать деньги игроку {user_id}"

    except Exception as e:
        print(f"❌ Ошибка при выдаче денег: {e}")
        return False, f"❌ Ошибка при выдаче денег: {str(e)}"


@admin_router.message(Command("add_money"))
async def handle_admin_add_money_command(message: Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора!")
        return

    if not command.args:
        await message.answer(
            "❌ **Использование:**\n\n"
            "`/add_money <user_id> <amount>` - выдать деньги во всех чатах\n"
            "`/add_money <user_id> <amount> <chat_id>` - выдать деньги в конкретном чате\n\n"
            "📌 **Примеры:**\n"
            "`/add_money 123456789 50000`\n"
            "`/add_money 123456789 50000 -1001234567890`",
            parse_mode="Markdown"
        )
        return

    args = command.args.split()

    if len(args) < 2:
        await message.answer(
            "❌ **Использование:**\n\n"
            "`/add_money <user_id> <amount>` - выдать деньги во всех чатах\n"
            "`/add_money <user_id> <amount> <chat_id>` - выдать деньги в конкретном чате",
            parse_mode="Markdown"
        )
        return

    try:
        target_user_id = int(args[0])
        amount = float(args[1])
        chat_id = None

        if len(args) == 3:
            chat_id = int(args[2])

        if amount <= 0:
            await message.answer("❌ Сумма должна быть положительным числом!")
            return

        success, result_message = await admin_add_money(target_user_id, amount, chat_id)
        await message.answer(result_message)

    except ValueError:
        await message.answer(
            "❌ **Неверный формат аргументов!**\n\n"
            "Убедитесь что:\n"
            "• user_id - целое число\n"
            "• amount - число\n"
            "• chat_id (опционально) - целое число (отрицательное для групп)",
            parse_mode="Markdown"
        )


async def admin_set_money(user_id: int, amount: float, chat_id: int = None) -> Tuple[bool, str]:
    return await asyncio.get_event_loop().run_in_executor(
        None, lambda: _admin_set_money_sync(user_id, amount, chat_id)
    )


def _admin_set_money_sync(user_id: int, amount: float, chat_id: int = None) -> Tuple[bool, str]:
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        if chat_id:
            cursor.execute('SELECT * FROM players WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
            player_data = cursor.fetchone()

            if not player_data:
                conn.close()
                return False, f"❌ Пользователь с ID {user_id} не найден в чате {chat_id}!"

            cursor.execute('''
            UPDATE players 
            SET money = ? 
            WHERE user_id = ? AND chat_id = ?
            ''', (amount, user_id, chat_id))

            conn.commit()
            conn.close()
            return True, f"✅ Игроку {user_id} установлено {int(amount)}💰 в чате {chat_id}!"
        else:
            cursor.execute('SELECT DISTINCT chat_id FROM players WHERE user_id = ?', (user_id,))
            games = cursor.fetchall()

            if not games:
                conn.close()
                return False, f"❌ Пользователь с ID {user_id} не найден в активных играх!"

            total_set = 0
            updated_chats = []

            for game in games:
                chat_id = game[0]
                cursor.execute('SELECT * FROM players WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
                player_data = cursor.fetchone()

                if player_data:
                    total_set += amount
                    updated_chats.append(chat_id)

                    cursor.execute('''
                    UPDATE players 
                    SET money = ? 
                    WHERE user_id = ? AND chat_id = ?
                    ''', (amount, user_id, chat_id))

            conn.commit()
            conn.close()

            if total_set > 0:
                return True, f"✅ Игроку {user_id} установлено {int(amount)}💰 в {len(updated_chats)} играх!\n💰 Всего установлено: {int(total_set)} монет"
            else:
                return False, f"❌ Не удалось установить деньги игроку {user_id}"

    except Exception as e:
        print(f"❌ Ошибка при установке денег: {e}")
        return False, f"❌ Ошибка при установке денег: {str(e)}"


@admin_router.message(Command("set_money"))
async def handle_admin_set_money_command(message: Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора!")
        return

    if not command.args:
        await message.answer(
            "❌ **Использование:**\n\n"
            "`/set_money <user_id> <amount>` - установить деньги во всех чатах\n"
            "`/set_money <user_id> <amount> <chat_id>` - установить деньги в конкретном чате\n\n"
            "📌 **Примеры:**\n"
            "`/set_money 123456789 100000`\n"
            "`/set_money 123456789 100000 -1001234567890`",
            parse_mode="Markdown"
        )
        return

    args = command.args.split()

    if len(args) < 2:
        await message.answer(
            "❌ **Использование:**\n\n"
            "`/set_money <user_id> <amount>` - установить деньги во всех чатах\n"
            "`/set_money <user_id> <amount> <chat_id>` - установить деньги в конкретном чате",
            parse_mode="Markdown"
        )
        return

    try:
        target_user_id = int(args[0])
        amount = float(args[1])
        chat_id = None

        if len(args) == 3:
            chat_id = int(args[2])

        if amount < 0:
            await message.answer("❌ Сумма не может быть отрицательной!")
            return

        success, result_message = await admin_set_money(target_user_id, amount, chat_id)
        await message.answer(result_message)

    except ValueError:
        await message.answer(
            "❌ **Неверный формат аргументов!**\n\n"
            "Убедитесь что:\n"
            "• user_id - целое число\n"
            "• amount - число\n"
            "• chat_id (опционально) - целое число (отрицательное для групп)",
            parse_mode="Markdown"
        )


@admin_router.message(Command("info"))
async def handle_game_info(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора!")
        return

    games_count = len(await get_all_games())
    
    total_players = 0
    games = await get_all_games()
    for chat_id in games.keys():
        players = await load_all_players(chat_id)
        total_players += len(players)

    info_text = (
        f"🎮 **ИНФОРМАЦИЯ О НАСТРОЙКАХ** 🎮\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**⚙️ ПАРАМЕТРЫ ИГРЫ:**\n"
        f"• ⏱️ **КД между войнами:** {WAR_COOLDOWN_MINUTES} мин\n"
        f"• ⏳ **Подготовка к войне:** {WAR_PREPARATION_SECONDS} сек\n"
        f"• ⚔️ **Длительность войны:** {WAR_DURATION_SECONDS} сек\n"
        f"• 💰 **Награда за победу:** 50% денег + 20% населения\n"
        f"• 🌍 **Количество стран:** {len(COUNTRIES)}\n\n"
        f"**🤝 СИСТЕМА СОЮЗНИКОВ:**\n"
        f"• Можно создавать постоянные союзы\n"
        f"• Совместные атаки с союзниками\n"
        f"• Союзники получают 20% бонус к силе\n"
        f"• Помощники получают 10% добычи\n\n"
        f"**📊 СТАТИСТИКА:**\n"
        f"• 🎮 **Активных игр:** {games_count}\n"
        f"• 👥 **Всего игроков:** {total_players}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👑 **Admin ID:** `{ADMIN_ID}`"
    )

    await message.answer(info_text, parse_mode="Markdown")


async def force_update_all_incomes():
    print("🔄 Принудительное обновление дохода для всех игроков...")
    games = await get_all_games()
    updated_count = 0
    
    for chat_id, game in games.items():
        if not game["war_active"] and not war_system.is_preparing(chat_id):
            players = await load_all_players(chat_id)
            for player in players.values():
                income = await update_player_income_in_db(player.user_id, chat_id)
                if income > 0:
                    updated_count += 1
    
    print(f"✅ Доход обновлен для {updated_count} игроков")


async def set_bot_commands():
    commands = [
        BotCommand(command="game", description="🎮 Создать/войти в игру"),
        BotCommand(command="join", description="🌍 Присоединиться к игре"),
        BotCommand(command="stats", description="📊 Показать статистику"),
        BotCommand(command="top", description="🏆 Топ игроков чата"),
        BotCommand(command="war", description="⚔️ Начать войну"),
        BotCommand(command="refresh", description="🔄 Обновить доход"),
        BotCommand(command="transfer", description="💸 Передать ресурсы"),
        BotCommand(command="help", description="❓ Помощь по игре"),
    ]

    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    print("✅ Команды меню установлены")


# ========== ЗАПУСК БОТА ==========

async def main():
    print("🚀 Запуск бота стратегии...")
    print(f"🌍 Доступно стран: {len(COUNTRIES)}")
    print(f"⚔️ КД между войнами: {WAR_COOLDOWN_MINUTES} мин")
    print(f"⏳ Подготовка к войне: {WAR_PREPARATION_SECONDS} сек")
    print(f"💰 Награда за войну: 50% денег + 20% населения")
    print(f"🔔 Включена система предупреждений о войне")
    print(f"🤝 Включена система союзников и совместных атак")

    init_database()

    dp.include_router(main_router)
    dp.include_router(callback_router)
    dp.include_router(admin_router)

    warning_task = asyncio.create_task(check_and_send_war_warnings())

    await set_bot_commands()

    print("✅ Бот запущен и готов к работе!")
    print("📊 Используйте /game в групповом чате чтобы начать")
    print(f"👑 Админ ID: {ADMIN_ID}")

    try:
        await dp.start_polling(bot)
    finally:
        warning_task.cancel()
        try:
            await warning_task
        except asyncio.CancelledError:
            print("🔔 Система предупреждений остановлена")


if __name__ == "__main__":
    asyncio.run(main())
