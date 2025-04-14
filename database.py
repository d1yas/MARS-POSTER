import sqlite3

# Baza bilan ulanish
connect = sqlite3.connect("bot_database.db")
cursor = connect.cursor()

# ==== JADVALLARNI YARATISH ====

# Guruhlarni saqlash uchun jadval
cursor.execute("""
CREATE TABLE IF NOT EXISTS active_groups (
    group_id TEXT PRIMARY KEY,
    group_name TEXT,
    joined_date TEXT
)
""")

# Rejalashtirilgan postlar uchun jadval
cursor.execute("""
CREATE TABLE IF NOT EXISTS active_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    photo TEXT,
    caption TEXT,
    post_time TEXT,
    status TEXT DEFAULT 'active',
    type TEXT DEFAULT 'photo'
)
""")

# Media guruhlar jadvali
cursor.execute("""
CREATE TABLE IF NOT EXISTS media_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    media_data TEXT NOT NULL,
    FOREIGN KEY (post_id) REFERENCES active_posts(id)
)
""")

# Har xil kontent turlari uchun universal postlar jadvali
cursor.execute("""
CREATE TABLE IF NOT EXISTS content_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_type TEXT,  -- 'text', 'photo', 'video', 'document', etc.
    media_id TEXT,      -- file_id for media, NULL for text
    caption TEXT,       -- caption or text content
    post_time TEXT,     -- comma-separated times
    status TEXT DEFAULT 'active'
)
""")

connect.commit()

# ==== FUNKSIYALAR ====

# Post qo‘shish funksiyasi
def add_post(photo, caption, post_time):
    cursor.execute("""
    INSERT INTO active_posts (photo, caption, post_time) 
    VALUES (?, ?, ?)
    """, (photo, caption, post_time))
    connect.commit()

# Har xil kontent qo‘shish funksiyasi
def add_content_post(content_type, media_id, caption, post_time):
    cursor.execute("""
    INSERT INTO content_posts (content_type, media_id, caption, post_time, status) 
    VALUES (?, ?, ?, ?, 'active')
    """, (content_type, media_id, caption, post_time))
    connect.commit()
    return cursor.lastrowid

# Postni olish
def get_post(post_id):
    return cursor.execute("""
    SELECT * FROM active_posts WHERE id = ?
    """, (post_id,)).fetchone()

# Post vaqtlarini olish (comma ajratilgan)
def get_post_times(post_id):
    result = cursor.execute("""
        SELECT post_time FROM active_posts WHERE id = ?
    """, (post_id,)).fetchone()

    if result and result[0]:
        return result[0].split(",")
    return []

# Post vaqtini yangilash
def updateting_post_time(post_id, post_time):
    cursor.execute("""
    UPDATE active_posts SET post_time = ? WHERE id = ?
    """, (post_time, post_id))
    connect.commit()

# Barcha aktiv postlarni olish
def get_active_posts():
    return cursor.execute("""
    SELECT * FROM active_posts WHERE status = 'active'
    """).fetchall()

# Postni "sent" sifatida belgilash
def mark_post_as_sent(post_id):
    cursor.execute("""
    UPDATE active_posts SET status = 'sent' WHERE id = ?
    """, (post_id,))
    connect.commit()


try:
    cursor.execute("ALTER TABLE active_posts ADD COLUMN type TEXT DEFAULT 'photo'")
except sqlite3.OperationalError:
    pass  # Ustun allaqachon mavjud
