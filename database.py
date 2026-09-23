import aiosqlite
import time

DB_NAME = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance REAL DEFAULT 0.0,
                ads_watched INTEGER DEFAULT 0,
                daily_ads INTEGER DEFAULT 0,
                last_ad_time REAL DEFAULT 0.0,
                referrals_count INTEGER DEFAULT 0,
                referred_by INTEGER
            )
        """)
        await db.commit()

async def add_user(user_id: int, referred_by: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        if not user:
            if referred_by == user_id:
                referred_by = None
                
            await db.execute(
                "INSERT INTO users (user_id, referred_by) VALUES (?, ?)", 
                (user_id, referred_by)
            )
            
            if referred_by:
                await db.execute(
                    "UPDATE users SET balance = balance + 2.0, referrals_count = referrals_count + 1 WHERE user_id = ?", 
                    (referred_by,)
                )
                
            await db.commit()
            return True
        return False

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT balance, ads_watched, daily_ads, last_ad_time, referrals_count FROM users WHERE user_id = ?", 
            (user_id,)
        )
        return await cursor.fetchone()

async def check_and_reset_daily_ads(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT daily_ads, last_ad_time FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        if row:
            daily_ads, last_ad_time = row
            current_time = time.time()
            if current_time - last_ad_time >= 86400:
                await db.execute("UPDATE users SET daily_ads = 0 WHERE user_id = ?", (user_id,))
                await db.commit()
                return 0, last_ad_time
            return daily_ads, last_ad_time
        return 0, 0.0

async def increment_ad(user_id: int):
    current_time = time.time()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE users SET balance = balance + 1.0, ads_watched = ads_watched + 1, daily_ads = daily_ads + 1, last_ad_time = ? WHERE user_id = ?", 
            (current_time, user_id)
        )
        await db.commit()

async def reset_balance(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = 0.0, ads_watched = 0, referrals_count = 0 WHERE user_id = ?", (user_id,))
        await db.commit()
