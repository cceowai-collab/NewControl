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
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, \
    BotCommandScopeDefault, FSInputFile
from aiogram.filters import Command, CommandObject
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# Конфигурация
TOKEN = os.getenv("BOT_TOKEN", "8614643355:AAGM2X4p-xTs6KNuEThKMo3hvYG2eFRkesQ")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5321542097"))

# Настройки базы данных
DATABASE_FILE = os.getenv("DATABASE_FILE", "game_database.db")
WAR_IMAGES_FOLDER = "war_images"

# Настройки игры
WAR_COOLDOWN_MINUTES = 2  # КД между войнами
WAR_DURATION_SECONDS = 30  # Длительность войны

# Создаем папку для изображений войны, если она не существует
if not os.path.exists(WAR_IMAGES_FOLDER):
    os.makedirs(WAR_IMAGES_FOLDER)
    print(f"📁 Создана папка для изображений войны: {WAR_IMAGES_FOLDER}")
    print(f"📝 Поместите изображения войны в папку {WAR_IMAGES_FOLDER}/")


@dataclass
class Country:
    """Класс страны"""
    name: str
    emoji: str
    base_income: float
    army_cost: int = 1000
    city_cost: int = 5000
    war_image: str = "war_default.jpg"
    color: str = "#FFD700"


# Список стран
COUNTRIES = {
    "russia": Country("Россия", "🇷🇺", 12.0, war_image="russia_war.jpg", color="#D52B1E"),
    "ukraine": Country("Украина", "🇺🇦", 9.0, war_image="ukraine_war.jpg", color="#0057B8"),
    "belarus": Country("Беларусь", "🇧🇾", 7.0, war_image="belarus_war.jpg", color="#D7332A"),
    "poland": Country("Польша", "🇵🇱", 10.0, war_image="poland_war.jpg", color="#DC143C"),
    "germany": Country("Германия", "🇩🇪", 15.0, war_image="germany_war.jpg", color="#000000"),
    "france": Country("Франция", "🇫🇷", 14.0, war_image="france_war.jpg", color="#0055A4"),
    "uk": Country("Великобритания", "🇬🇧", 13.0, war_image="uk_war.jpg", color="#012169"),
    "italy": Country("Италия", "🇮🇹", 12.0, war_image="italy_war.jpg", color="#009246"),
    "spain": Country("Испания", "🇪🇸", 11.0, war_image="spain_war.jpg", color="#AA151B"),
    "sweden": Country("Швеция", "🇸🇪", 10.0, war_image="sweden_war.jpg", color="#006AA7"),
    "norway": Country("Норвегия", "🇳🇴", 9.0, war_image="norway_war.jpg", color="#BA0C2F"),
    "finland": Country("Финляндия", "🇫🇮", 8.0, war_image="finland_war.jpg", color="#003580"),
    "denmark": Country("Дания", "🇩🇰", 8.5, war_image="denmark_war.jpg", color="#C8102E"),
    "greece": Country("Греция", "🇬🇷", 8.0, war_image="greece_war.jpg", color="#0D5EAF"),
    "portugal": Country("Португалия", "🇵🇹", 8.0, war_image="portugal_war.jpg", color="#006600"),
    "croatia": Country("Хорватия", "🇭🇷", 7.0, war_image="croatia_war.jpg", color="#FF0000"),
    "serbia": Country("Сербия", "🇷🇸", 7.0, war_image="serbia_war.jpg", color="#C6363C"),
    "austria": Country("Австрия", "🇦🇹", 9.0, war_image="austria_war.jpg", color="#ED2939"),
    "switzerland": Country("Швейцария", "🇨🇭", 11.0, war_image="switzerland_war.jpg", color="#FF0000"),
    "czech": Country("Чехия", "🇨🇿", 8.5, war_image="czech_war.jpg", color="#11457E"),
    "hungary": Country("Венгрия", "🇭🇺", 7.5, war_image="hungary_war.jpg", color="#CD2A3E"),
    "netherlands": Country("Нидерланды", "🇳🇱", 10.0, war_image="netherlands_war.jpg", color="#21468B"),
    "belgium": Country("Бельгия", "🇧🇪", 9.0, war_image="belgium_war.jpg", color="#000000"),
    "luxembourg": Country("Люксембург", "🇱🇺", 12.0, war_image="luxembourg_war.jpg", color="#00A1DE"),
    "romania": Country("Румыния", "🇷🇴", 7.0, war_image="romania_war.jpg", color="#002B7F"),
    "bulgaria": Country("Болгария", "🇧🇬", 6.5, war_image="bulgaria_war.jpg", color="#00966E"),
    "albania": Country("Албания", "🇦🇱", 6.0, war_image="albania_war.jpg", color="#E41E20"),
    "latvia": Country("Латвия", "🇱🇻", 6.5, war_image="latvia_war.jpg", color="#9E3039"),
    "lithuania": Country("Литва", "🇱🇹", 6.5, war_image="lithuania_war.jpg", color="#FDB913"),
    "estonia": Country("Эстония", "🇪🇪", 6.5, war_image="estonia_war.jpg", color="#0072CE"),
    "turkey": Country("Турция", "🇹🇷", 9.5, war_image="turkey_war.jpg", color="#E30A17"),
    "ireland": Country("Ирландия", "🇮🇪", 8.5, war_image="ireland_war.jpg", color="#169B62"),
    "iceland": Country("Исландия", "🇮🇸", 7.0, war_image="iceland_war.jpg", color="#003897"),
    "slovakia": Country("Словакия", "🇸🇰", 7.0, war_image="slovakia_war.jpg", color="#0B4EA2"),
    "slovenia": Country("Словения", "🇸🇮", 7.0, war_image="slovenia_war.jpg", color="#FF0000"),
}


@dataclass
class Player:
    """Класс игрока"""
    user_id: int
    username: str
    country: str
    money: float = 1000.0
    army_level: int = 1
    city_level: int = 1
    last_income: datetime = field(default_factory=datetime.now)
    wins: int = 0
    losses: int = 0


# ========== ИСПРАВЛЕННЫЙ КЛАСС TRANSFERDATA ==========
class TransferData:
    """Класс для временного хранения данных перевода"""

    def __init__(self):
        self.transfers = {}  # user_id -> {"target_id": int, "type": str, "chat_id": int}


transfer_data = TransferData()


class WarWarningSystem:
    """Система предупреждений о войне"""

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
                            f"💰 Успейте подготовиться!\n\n"
                            f"⚔️ Победитель получит 50% ресурсов проигравшего!"
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
            last_income TEXT, 
            wins INTEGER DEFAULT 0, 
            losses INTEGER DEFAULT 0, 
            chat_id INTEGER,
            FOREIGN KEY (chat_id) REFERENCES games (chat_id), 
            UNIQUE(user_id, chat_id)
        )
    ''')

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
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute('''
    INSERT OR REPLACE INTO players 
    (user_id, username, country, money, army_level, city_level, last_income, wins, losses, chat_id)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        player.user_id, player.username, player.country, player.money,
        player.army_level, player.city_level, player.last_income.isoformat(),
        player.wins, player.losses, chat_id
    ))

    conn.commit()
    conn.close()


async def load_game(chat_id: int) -> Optional[Dict]:
    return await asyncio.get_event_loop().run_in_executor(None, lambda: _load_game_sync(chat_id))


def _load_game_sync(chat_id: int) -> Optional[Dict]:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games WHERE chat_id = ?', (chat_id,))
    game_data = cursor.fetchone()
    conn.close()

    if not game_data:
        return None

    return {
        "chat_id": game_data[0],
        "creator_id": game_data[1],
        "war_active": bool(game_data[2]),
        "war_participants": json.loads(game_data[3]) if game_data[3] else [],
        "war_start_time": datetime.fromisoformat(game_data[4]) if game_data[4] else None,
        "last_war": datetime.fromisoformat(game_data[5]) if game_data[5] else None
    }


async def load_player(user_id: int, chat_id: int) -> Optional[Player]:
    return await asyncio.get_event_loop().run_in_executor(None, lambda: _load_player_sync(user_id, chat_id))


def _load_player_sync(user_id: int, chat_id: int) -> Optional[Player]:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    player_data = cursor.fetchone()
    conn.close()

    if not player_data:
        return None

    return Player(
        user_id=player_data[1],
        username=player_data[2],
        country=player_data[3],
        money=player_data[4],
        army_level=player_data[5],
        city_level=player_data[6],
        last_income=datetime.fromisoformat(player_data[7]),
        wins=player_data[8],
        losses=player_data[9]
    )


async def load_all_players(chat_id: int) -> Dict[int, Player]:
    return await asyncio.get_event_loop().run_in_executor(None, lambda: _load_all_players_sync(chat_id))


def _load_all_players_sync(chat_id: int) -> Dict[int, Player]:
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM players WHERE chat_id = ?', (chat_id,))
    players_data = cursor.fetchall()
    conn.close()

    players = {}
    for player_data in players_data:
        player = Player(
            user_id=player_data[1],
            username=player_data[2],
            country=player_data[3],
            money=player_data[4],
            army_level=player_data[5],
            city_level=player_data[6],
            last_income=datetime.fromisoformat(player_data[7]),
            wins=player_data[8],
            losses=player_data[9]
        )
        players[player.user_id] = player

    return players


async def update_player_income_in_db(user_id: int, chat_id: int) -> float:
    return await asyncio.get_event_loop().run_in_executor(None,
                                                          lambda: _update_player_income_in_db_sync(user_id, chat_id))


def _update_player_income_in_db_sync(user_id: int, chat_id: int) -> float:
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM players WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
        player_data = cursor.fetchone()

        if not player_data:
            conn.close()
            return 0

        player = Player(
            user_id=player_data[1],
            username=player_data[2],
            country=player_data[3],
            money=player_data[4],
            army_level=player_data[5],
            city_level=player_data[6],
            last_income=datetime.fromisoformat(player_data[7]),
            wins=player_data[8],
            losses=player_data[9]
        )

        current_time = datetime.now()
        time_diff = (current_time - player.last_income).total_seconds()

        if time_diff > 0:
            country = COUNTRIES.get(player.country)
            if country:
                income = country.base_income * player.city_level * time_diff
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
                    conn.close()
                    return income
        conn.close()
        return 0
    except Exception as e:
        print(f"❌ Ошибка обновления дохода: {e}")
        return 0


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
            "war_active": bool(game_data[2]),
            "war_participants": json.loads(game_data[3]) if game_data[3] else [],
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
        width=1
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


async def get_players_keyboard(chat_id: int, exclude_id: int, transfer_type: str,
                               current_player_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора игрока для передачи"""
    builder = InlineKeyboardBuilder()
    players = await load_all_players(chat_id)

    # Сортируем игроков по имени
    sorted_players = sorted(players.values(), key=lambda p: p.username)

    for player in sorted_players:
        if player.user_id != exclude_id:
            country = COUNTRIES.get(player.country)
            if country:
                # Формируем правильный callback_data
                callback_data = f"transfer_target_{transfer_type}_{player.user_id}_{current_player_id}_{chat_id}"
                builder.row(
                    InlineKeyboardButton(
                        text=f"{country.emoji} {player.username}",
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

    sorted_players = sorted(players.values(), key=lambda p: p.army_level, reverse=True)

    for player in sorted_players:
        if player.user_id != attacker_id:
            country = COUNTRIES.get(player.country)
            if country:
                power_indicator = "💪" * min(player.army_level, 3)
                if player.army_level > 3:
                    power_indicator = "💪💪💪+"

                builder.row(
                    InlineKeyboardButton(
                        text=f"{country.emoji} {player.username} ⚔️{player.army_level} {power_indicator}",
                        callback_data=f"wartarget_{player.user_id}_{attacker_id}_{chat_id}"
                    ),
                    width=1
                )

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{attacker_id}_{chat_id}"),
        width=1
    )

    return builder.as_markup()


def get_countries_keyboard(player_id: int, chat_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Простая клавиатура со всеми странами
    countries_list = list(COUNTRIES.items())

    for i in range(0, len(countries_list), 3):
        row = countries_list[i:i + 3]
        buttons = []
        for country_id, country in row:
            buttons.append(
                InlineKeyboardButton(
                    text=f"{country.emoji} {country.name}",
                    callback_data=f"country_{country_id}_{player_id}_{chat_id}"
                )
            )
        builder.row(*buttons, width=len(buttons))

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_{player_id}_{chat_id}"),
        width=1
    )

    return builder.as_markup()


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
            caption=f"⚔️ {attacker_country.emoji} **{attacker_country.name}** vs {target_country.emoji} **{target_country.name}** ⚔️",
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

    income_per_sec = country.base_income * updated_player.city_level
    army_upgrade_cost = country.army_cost * updated_player.army_level
    city_upgrade_cost = country.city_cost * updated_player.city_level

    army_indicator = "■" * min(updated_player.army_level, 10) + "□" * max(0, 10 - min(updated_player.army_level, 10))
    city_indicator = "■" * min(updated_player.city_level, 10) + "□" * max(0, 10 - min(updated_player.city_level, 10))

    win_rate = (updated_player.wins / (updated_player.wins + updated_player.losses) * 100) if (
                                                                                                          updated_player.wins + updated_player.losses) > 0 else 0

    text = (
        f"🎮 **ИГРОВОЙ ПРОФИЛЬ** 🎮\n\n"
        f"**{country.emoji} {country.name}**\n"
        f"👤 **Игрок:** {updated_player.username}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **Казна:** `{int(updated_player.money):,}` монет\n"
        f"📈 **Доход:** `{income_per_sec:.1f}` монет/сек\n\n"
        f"⚔️ **Армия:** Уровень {updated_player.army_level}\n"
        f"`{army_indicator}`\n"
        f"🏙️ **Город:** Уровень {updated_player.city_level}\n"
        f"`{city_indicator}`\n\n"
        f"📊 **Статистика:**\n"
        f"🏆 Победы: `{updated_player.wins}` | 💀 Поражения: `{updated_player.losses}`\n"
        f"📈 Win Rate: `{win_rate:.1f}%`\n\n"
        f"💰 **Стоимость улучшений:**\n"
        f"⚔️ Армия: `{army_upgrade_cost:,}` монет\n"
        f"🏙️ Город: `{city_upgrade_cost:,}` монет"
    )

    try:
        await message.edit_text(text, reply_markup=get_game_keyboard(updated_player.user_id, chat_id),
                                parse_mode="Markdown")
    except TelegramBadRequest:
        await message.answer(text, reply_markup=get_game_keyboard(updated_player.user_id, chat_id),
                             parse_mode="Markdown")


async def end_war(chat_id: int):
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
    target = await load_player(war_participants[1], chat_id)

    if not attacker or not target:
        game["war_active"] = False
        game["war_participants"] = []
        await save_game(chat_id, game["creator_id"], False, [], None, datetime.now())
        return

    attacker_power = attacker.army_level * (1 + attacker.city_level * 0.05) * (1 + random.uniform(-0.1, 0.1))
    target_power = target.army_level * (1 + target.city_level * 0.05) * (1 + random.uniform(-0.1, 0.1))

    if attacker_power > target_power:
        winner = attacker
        loser = target
        winner_was_attacker = True
    else:
        winner = target
        loser = attacker
        winner_was_attacker = False

    money_reward = int(loser.money * 0.5)
    army_reward = max(1, int(loser.army_level * 0.5))

    winner.money += money_reward
    winner.army_level += army_reward

    loser.money = max(0, loser.money - money_reward)
    loser.army_level = max(1, loser.army_level - army_reward)

    winner.wins += 1
    loser.losses += 1

    await save_player(winner, chat_id)
    await save_player(loser, chat_id)

    game["war_active"] = False
    game["war_participants"] = []
    game["last_war"] = datetime.now()
    await save_game(chat_id, game["creator_id"], False, [], None, datetime.now())

    winner_country = COUNTRIES.get(winner.country)
    loser_country = COUNTRIES.get(loser.country)

    if winner_was_attacker:
        war_role = "⚔️ АТАКУЮЩИЙ"
    else:
        war_role = "🛡️ ЗАЩИЩАЮЩИЙСЯ"

    result_text = (
        f"⚔️ **ВОЙНА ЗАВЕРШЕНА!** ⚔️\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 **ПОБЕДИТЕЛЬ ({war_role})**\n"
        f"{winner_country.emoji} **{winner.username}**\n\n"
        f"💀 **ПРОИГРАВШИЙ**\n"
        f"{loser_country.emoji} **{loser.username}**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **Добыча:** `{money_reward:,}` монет\n"
        f"🎖️ **Военная добыча:** +{army_reward} уровней армии\n"
        f"⚔️ **Новая сила:** {winner.army_level} уровень\n\n"
        f"💸 **У проигравшего осталось:** `{int(loser.money):,}` монет\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Следующая война через {WAR_COOLDOWN_MINUTES} минуты"
    )

    await bot.send_message(chat_id=chat_id, text=result_text, parse_mode="Markdown")


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
            "⚔️ **Особенности:**\n"
            "• Выбирайте страну и развивайте её\n"
            "• Зарабатывайте пассивный доход\n"
            "• Улучшайте армию и город\n"
            "• Вступайте в войны с другими игроками\n\n"
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
        "**📈 КАК ИГРАТЬ:**\n"
        "1️⃣ Создайте игру в групповом чате\n"
        "2️⃣ Выберите страну\n"
        "3️⃣ Улучшайте армию и город\n"
        "4️⃣ Зарабатывайте пассивный доход\n"
        "5️⃣ Нападайте на других игроков\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**⚔️ ВОЙНА:**\n"
        "• Победитель получает 50% ресурсов\n"
        "• КД между войнами: 2 минуты\n"
        "• Длительность битвы: 30 секунд\n\n"
        "**💰 ПАССИВНЫЙ ДОХОД:**\n"
        "• Начисляется каждую секунду\n"
        "• Зависит от страны и уровня города\n"
        "• Используйте /refresh для обновления"
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

    player = await load_player(user_id, chat_id)
    if player:
        await message.answer("✅ Вы уже в игре!")
        await update_player_menu(message, player, chat_id)
        return

    await message.answer(
        "🌍 **ВЫБЕРИТЕ СТРАНУ** 🌍\n\n"
        "Каждая страна имеет уникальный доход:\n"
        "• 🇩🇪 Германия: 15💰/сек\n"
        "• 🇫🇷 Франция: 14💰/сек\n"
        "• 🇬🇧 Великобритания: 13💰/сек\n"
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

    income_per_sec = country.base_income * updated_player.city_level
    army_upgrade_cost = country.army_cost * updated_player.army_level
    city_upgrade_cost = country.city_cost * updated_player.city_level

    army_indicator = "■" * min(updated_player.army_level, 10) + "□" * max(0, 10 - min(updated_player.army_level, 10))
    city_indicator = "■" * min(updated_player.city_level, 10) + "□" * max(0, 10 - min(updated_player.city_level, 10))

    win_rate = (updated_player.wins / (updated_player.wins + updated_player.losses) * 100) if (
                                                                                                          updated_player.wins + updated_player.losses) > 0 else 0

    text = (
        f"📊 **СТАТИСТИКА** 📊\n\n"
        f"**{country.emoji} {country.name}**\n"
        f"👤 **Игрок:** {updated_player.username}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **Казна:** `{int(updated_player.money):,}` монет\n"
        f"📈 **Доход:** `{income_per_sec:.1f}` монет/сек\n\n"
        f"⚔️ **Армия:** Уровень {updated_player.army_level}\n"
        f"`{army_indicator}`\n"
        f"🏙️ **Город:** Уровень {updated_player.city_level}\n"
        f"`{city_indicator}`\n\n"
        f"🏆 **Победы:** `{updated_player.wins}` | 💀 **Поражения:** `{updated_player.losses}`\n"
        f"📊 **Win Rate:** `{win_rate:.1f}%`\n\n"
        f"💰 **Стоимость улучшений:**\n"
        f"⚔️ Армия: `{army_upgrade_cost:,}` монет\n"
        f"🏙️ Город: `{city_upgrade_cost:,}` монет"
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
    sorted_players = sorted(players.values(), key=lambda p: p.money, reverse=True)

    top_text = f"🏆 **ТОП ИГРОКОВ ЧАТА** 🏆\n\n"
    top_text += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for i, player in enumerate(sorted_players[:10], 1):
        country = COUNTRIES.get(player.country)
        emoji = country.emoji if country else "🏳️"
        medal = medals[i - 1] if i <= 3 else f"{i}."

        top_text += f"{medal} {emoji} **{player.username}**\n"
        top_text += f"   💰 `{int(player.money):,}` | ⚔️{player.army_level} | 🏙️{player.city_level}\n\n"

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

    if game["last_war"]:
        time_since_last_war = datetime.now() - game["last_war"]
        if time_since_last_war < timedelta(minutes=WAR_COOLDOWN_MINUTES):
            remaining = timedelta(minutes=WAR_COOLDOWN_MINUTES) - time_since_last_war
            minutes = int(remaining.total_seconds() // 60)
            seconds = int(remaining.total_seconds() % 60)
            await message.answer(f"⏳ **До следующей войны:** `{minutes}:{seconds:02d}`")
            return

    player = await load_player(user_id, chat_id)
    if not player:
        await message.answer("❌ Вы не в игре! Используйте /join")
        return

    players = await load_all_players(chat_id)
    if len(players) < 2:
        await message.answer("❌ Недостаточно игроков для войны!")
        return

    await message.answer(
        f"⚔️ **ВЫБЕРИТЕ ЦЕЛЬ ДЛЯ АТАКИ** ⚔️\n\n"
        f"**Ваша сила:** ⚔️{player.army_level} | 🏙️{player.city_level}",
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
        await message.answer(f"✅ **Начислено:** `{income:.1f}` монет!")
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

    if game["war_active"]:
        await message.answer("⚔️ Нельзя передавать ресурсы во время войны!")
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
        f"💰 **Ваш баланс:** `{int(player.money):,}` монет\n"
        f"⚔️ **Уровень армии:** {player.army_level}\n\n"
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
        await save_player(existing_player, chat_id)
        await callback.message.edit_text(
            f"✅ **Страна изменена!**\n\n"
            f"🌍 **Новая страна:** {country.emoji} {country.name}\n"
            f"📈 **Новый доход:** `{country.base_income * existing_player.city_level:.1f}` монет/сек",
            parse_mode="Markdown"
        )
        await update_player_menu(callback.message, existing_player, chat_id)
    else:
        player = Player(
            user_id=user_id,
            username=callback.from_user.username or callback.from_user.first_name,
            country=country_id,
            last_income=datetime.now()
        )
        await save_player(player, chat_id)
        await callback.message.edit_text(
            f"🎉 **ДОБРО ПОЖАЛОВАТЬ!** 🎉\n\n"
            f"🌍 **Страна:** {country.emoji} {country.name}\n"
            f"💰 **Стартовый капитал:** `{int(player.money):,}` монет\n"
            f"⚔️ **Армия:** {player.army_level} уровень\n"
            f"🏙️ **Город:** {player.city_level} уровень\n"
            f"📈 **Доход:** `{country.base_income * player.city_level:.1f}` монет/сек",
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

    income_per_sec = country.base_income * player.city_level
    army_upgrade_cost = country.army_cost * player.army_level
    city_upgrade_cost = country.city_cost * player.city_level

    army_indicator = "■" * min(player.army_level, 10) + "□" * max(0, 10 - min(player.army_level, 10))
    city_indicator = "■" * min(player.city_level, 10) + "□" * max(0, 10 - min(player.city_level, 10))

    win_rate = (player.wins / (player.wins + player.losses) * 100) if (player.wins + player.losses) > 0 else 0

    text = (
        f"📊 **СТАТИСТИКА** 📊\n\n"
        f"**{country.emoji} {country.name}**\n"
        f"👤 **Игрок:** {player.username}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **Казна:** `{int(player.money):,}` монет\n"
        f"📈 **Доход:** `{income_per_sec:.1f}` монет/сек\n\n"
        f"⚔️ **Армия:** Уровень {player.army_level}\n"
        f"`{army_indicator}`\n"
        f"🏙️ **Город:** Уровень {player.city_level}\n"
        f"`{city_indicator}`\n\n"
        f"🏆 **Победы:** `{player.wins}` | 💀 **Поражения:** `{player.losses}`\n"
        f"📊 **Win Rate:** `{win_rate:.1f}%`\n\n"
        f"💰 **След. улучшение:**\n"
        f"⚔️ Армия: `{army_upgrade_cost:,}` монет\n"
        f"🏙️ Город: `{city_upgrade_cost:,}` монет"
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

    if game["war_active"]:
        await callback.answer("⚔️ Нельзя улучшать армию во время войны!")
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
        await callback.answer(f"❌ Недостаточно денег! Нужно `{upgrade_cost:,}`💰")
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

    if game["war_active"]:
        await callback.answer("⚔️ Нельзя улучшать город во время войны!")
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
        await callback.answer(f"❌ Недостаточно денег! Нужно `{upgrade_cost:,}`💰")
        return

    player.money -= upgrade_cost
    player.city_level += 1
    await save_player(player, chat_id)

    await callback.answer(f"✅ Город улучшен до {player.city_level} уровня!")

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
    sorted_players = sorted(players.values(), key=lambda p: p.money, reverse=True)

    top_text = f"🏆 **ТОП ИГРОКОВ** 🏆\n\n"
    top_text += f"━━━━━━━━━━━━━━━━━━━━\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for i, player in enumerate(sorted_players[:10], 1):
        country = COUNTRIES.get(player.country)
        emoji = country.emoji if country else "🏳️"
        medal = medals[i - 1] if i <= 3 else f"{i}."

        top_text += f"{medal} {emoji} **{player.username}**\n"
        top_text += f"   💰 `{int(player.money):,}` | ⚔️{player.army_level} | 🏙️{player.city_level}\n\n"

    top_text += f"━━━━━━━━━━━━━━━━━━━━"

    await callback.message.edit_text(top_text, reply_markup=get_back_keyboard(user_id, chat_id),
                                     parse_mode="Markdown")
    await callback.answer()


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

    await callback.message.edit_text(
        f"⚔️ **ВЫБЕРИТЕ ЦЕЛЬ ДЛЯ АТАКИ** ⚔️\n\n"
        f"**Ваша сила:** ⚔️{player.army_level} | 🏙️{player.city_level}",
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

    attacker = await load_player(attacker_id, chat_id)
    if not attacker:
        await callback.answer("❌ Вы не в игре!")
        return

    target = await load_player(target_player_id, chat_id)
    if not target:
        await callback.answer("❌ Цель не найдена!")
        return

    await update_player_income_in_db(attacker_id, chat_id)
    await update_player_income_in_db(target_player_id, chat_id)

    attacker = await load_player(attacker_id, chat_id)
    target = await load_player(target_player_id, chat_id)

    war_participants = [attacker.user_id, target.user_id]
    game["war_active"] = True
    game["war_participants"] = war_participants
    game["war_start_time"] = datetime.now()
    await save_game(chat_id, game["creator_id"], True, war_participants, datetime.now(), game["last_war"])

    attacker_country = COUNTRIES.get(attacker.country)
    target_country = COUNTRIES.get(target.country)

    if attacker_country and target_country:
        await send_war_image(chat_id, attacker_country, target_country)

    war_text = (
        f"⚔️ **ВОЙНА НАЧАЛАСЬ!** ⚔️\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{attacker_country.emoji} **{attacker.username}**\n"
        f"     VS\n"
        f"{target_country.emoji} **{target.username}**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Силы сторон:**\n"
        f"⚔️ {attacker.username}: {attacker.army_level} уровень\n"
        f"⚔️ {target.username}: {target.army_level} уровень\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💰 **Награда:** 50% ресурсов проигравшего\n"
        f"⏳ **Битва продлится** {WAR_DURATION_SECONDS} секунд..."
    )

    await callback.message.edit_text(war_text, parse_mode="Markdown")

    await asyncio.sleep(WAR_DURATION_SECONDS)
    await end_war(chat_id)


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

    if game["war_active"]:
        await callback.answer("⚔️ Нельзя менять страну во время войны!")
        return

    await callback.message.edit_text(
        "🌍 **ВЫБЕРИТЕ НОВУЮ СТРАНУ** 🌍",
        reply_markup=get_countries_keyboard(user_id, chat_id),
        parse_mode="Markdown"
    )
    await callback.answer()


# ========== ИСПРАВЛЕННЫЕ ОБРАБОТЧИКИ ПЕРЕВОДА ==========

@callback_router.callback_query(F.data.startswith("transfer_menu_"))
async def handle_transfer_menu(callback: CallbackQuery):
    """Обработка выбора типа перевода из меню"""
    try:
        # Формат: transfer_menu_money_userid_chatid или transfer_menu_army_userid_chatid
        parts = callback.data.split('_')
        if len(parts) != 5:
            await callback.answer("❌ Ошибка формата данных!")
            return

        transfer_type = parts[2]  # money или army
        user_id = int(parts[3])
        chat_id = int(parts[4])

        if callback.from_user.id != user_id:
            await callback.answer("❌ Это не ваша кнопка!")
            return

        game = await load_game(chat_id)
        if not game:
            await callback.answer("❌ Игра не найдена!")
            return

        if game["war_active"]:
            await callback.answer("⚔️ Нельзя передавать ресурсы во время войны!")
            return

        await update_player_income_in_db(user_id, chat_id)

        player = await load_player(user_id, chat_id)
        if not player:
            await callback.answer("❌ Вы не в игре!")
            return

        if transfer_type == "money":
            text = f"💸 **ПЕРЕДАЧА ДЕНЕГ** 💸\n\n💰 **Ваш баланс:** `{int(player.money):,}` монет\n\n**Выберите получателя:**"
        else:  # army
            text = f"🎖️ **ПЕРЕДАЧА АРМИИ** 🎖️\n\n⚔️ **Ваша армия:** {player.army_level} уровень\n\n**Выберите получателя:**"

        await callback.message.edit_text(
            text,
            reply_markup=await get_players_keyboard(chat_id, user_id, transfer_type, user_id),
            parse_mode="Markdown"
        )
        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в transfer_menu: {e}")
        await callback.answer("❌ Произошла ошибка!")


@callback_router.callback_query(F.data.startswith("transfer_target_"))
async def handle_transfer_target(callback: CallbackQuery):
    """Обработка выбора цели для передачи"""
    try:
        # Формат: transfer_target_money_targetid_senderid_chatid
        parts = callback.data.split('_')
        if len(parts) != 6:
            await callback.answer("❌ Ошибка формата данных!")
            return

        transfer_type = parts[2]  # money или army
        target_id = int(parts[3])
        sender_id = int(parts[4])
        chat_id = int(parts[5])

        if callback.from_user.id != sender_id:
            await callback.answer("❌ Это не ваша кнопка!")
            return

        game = await load_game(chat_id)
        if not game:
            await callback.answer("❌ Игра не найдена!")
            return

        if game["war_active"]:
            await callback.answer("⚔️ Нельзя передавать ресурсы во время войны!")
            return

        sender = await load_player(sender_id, chat_id)
        if not sender:
            await callback.answer("❌ Вы не в игре!")
            return

        receiver = await load_player(target_id, chat_id)
        if not receiver:
            await callback.answer("❌ Получатель не найден!")
            return

        # Сохраняем данные о переводе
        transfer_data.transfers[sender_id] = {
            "target_id": target_id,
            "type": transfer_type,
            "chat_id": chat_id
        }

        if transfer_type == "money":
            max_amount = int(sender.money)
            await callback.message.edit_text(
                f"💸 **ПЕРЕДАЧА ДЕНЕГ** 💸\n\n"
                f"👤 **Получатель:** {receiver.username}\n"
                f"💰 **Ваш баланс:** `{max_amount:,}` монет\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"✏️ **Введите сумму для передачи** (целое число, макс. {max_amount}):",
                parse_mode="Markdown"
            )
        else:  # army
            max_transfer = sender.army_level - 1
            if max_transfer <= 0:
                await callback.message.edit_text(
                    "❌ **У вас минимальный уровень армии!**\n\n"
                    "Нельзя передать последний уровень.",
                    reply_markup=get_back_keyboard(sender_id, chat_id),
                    parse_mode="Markdown"
                )
                del transfer_data.transfers[sender_id]
                await callback.answer()
                return

            await callback.message.edit_text(
                f"🎖️ **ПЕРЕДАЧА АРМИИ** 🎖️\n\n"
                f"👤 **Получатель:** {receiver.username}\n"
                f"⚔️ **Ваша армия:** {sender.army_level} уровень\n"
                f"📊 **Максимум:** {max_transfer} уровней\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"✏️ **Введите количество уровней** для передачи (1-{max_transfer}):",
                parse_mode="Markdown"
            )

        await callback.answer()

    except Exception as e:
        print(f"❌ Ошибка в transfer_target: {e}")
        await callback.answer("❌ Произошла ошибка!")


@main_router.message(lambda message: message.from_user.id in transfer_data.transfers)
async def handle_transfer_amount(message: Message):
    """Обработка ввода суммы перевода"""
    user_id = message.from_user.id

    if user_id not in transfer_data.transfers:
        return

    transfer_info = transfer_data.transfers[user_id]
    target_id = transfer_info["target_id"]
    transfer_type = transfer_info["type"]
    chat_id = transfer_info["chat_id"]

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
            await message.answer(f"❌ Недостаточно денег! У вас только `{int(sender.money):,}`💰")
            del transfer_data.transfers[user_id]
            return

        sender.money -= amount
        receiver.money += amount

        await save_player(sender, chat_id)
        await save_player(receiver, chat_id)

        await message.answer(
            f"✅ **Перевод выполнен успешно!**\n\n"
            f"💰 **Сумма:** `{amount:,}` монет\n"
            f"👤 **Получатель:** {receiver.username}\n"
            f"💳 **Ваш баланс:** `{int(sender.money):,}` монет",
            parse_mode="Markdown"
        )

        try:
            await bot.send_message(
                chat_id=target_id,
                text=f"💰 **Получен перевод!**\n\n"
                     f"👤 **От:** {sender.username}\n"
                     f"💰 **Сумма:** `{amount:,}` монет\n"
                     f"💳 **Ваш баланс:** `{int(receiver.money):,}` монет",
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
            await message.answer(f"❌ Вы можете передать максимум `{sender.army_level - 1}` уровней!")
            del transfer_data.transfers[user_id]
            return

        sender.army_level -= amount
        receiver.army_level += amount

        await save_player(sender, chat_id)
        await save_player(receiver, chat_id)

        await message.answer(
            f"✅ **Передача армии выполнена!**\n\n"
            f"🎖️ **Передано:** {amount} уровней армии\n"
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
        await message.answer("❌ Использование: /add_money <user_id> <amount> [chat_id]")
        return

    args = command.args.split()

    if len(args) < 2:
        await message.answer("❌ Использование: /add_money <user_id> <amount> [chat_id]")
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
        await message.answer("❌ Неверный формат аргументов!")


@admin_router.message(Command("set_money"))
async def handle_admin_set_money_command(message: Message, command: CommandObject):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора!")
        return

    if not command.args:
        await message.answer("❌ Использование: /set_money <user_id> <amount> [chat_id]")
        return

    args = command.args.split()

    if len(args) < 2:
        await message.answer("❌ Использование: /set_money <user_id> <amount> [chat_id]")
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
        await message.answer("❌ Неверный формат аргументов!")


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


@admin_router.message(Command("info"))
async def handle_game_info(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ У вас нет прав администратора!")
        return

    info_text = (
        f"🎮 **ИНФОРМАЦИЯ О НАСТРОЙКАХ** 🎮\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⏱️ **КД между войнами:** {WAR_COOLDOWN_MINUTES} минуты\n"
        f"⚔️ **Длительность войны:** {WAR_DURATION_SECONDS} секунд\n"
        f"💰 **Награда за победу:** 50% ресурсов\n"
        f"🌍 **Количество стран:** {len(COUNTRIES)}\n"
        f"📊 **Всего игр в базе:** {len(await get_all_games())}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

    await message.answer(info_text, parse_mode="Markdown")


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


async def force_update_all_incomes():
    print("🔄 Принудительное обновление дохода для всех игроков...")
    games = await get_all_games()
    for chat_id, game in games.items():
        if not game["war_active"]:
            players = await load_all_players(chat_id)
            for player in players.values():
                await update_player_income_in_db(player.user_id, chat_id)
    print("✅ Доход обновлен для всех игроков")


# ========== ЗАПУСК БОТА ==========

async def main():
    print("🚀 Запуск бота стратегии...")
    print(f"🌍 Доступно стран: {len(COUNTRIES)}")
    print(f"⚔️ КД между войнами: {WAR_COOLDOWN_MINUTES} мин")
    print(f"💰 Награда за войну: 50% ресурсов")
    print(f"🔔 Включена система предупреждений о войне")

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