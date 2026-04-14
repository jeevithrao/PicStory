# app/db/connection.py
# MySQL connection pool + init_db() that auto-creates all 6 tables on startup.
# Call get_connection() from any service to get a live DB connection.

import mysql.connector
from mysql.connector import pooling
from app.config import settings

# ---------------------------------------------------------------------------
# Connection Pool (reuses connections instead of opening a new one each time)
# ---------------------------------------------------------------------------
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="picstory_pool",
            pool_size=5,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
        )
    return _pool

def get_connection():
    """Return a connection from the pool. Always close() it after use."""
    return get_pool().get_connection()


# ---------------------------------------------------------------------------
# init_db() — called once when the server starts (from main.py lifespan)
# Creates the DB if missing, then creates all 6 tables if they don't exist.
# ---------------------------------------------------------------------------
def init_db():
    # Step 1: Connect without specifying a database to create it if needed
    raw = mysql.connector.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )
    cur = raw.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{settings.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cur.execute(f"USE `{settings.DB_NAME}`;")
    raw.commit()

    # Step 2: Create all 6 tables
    tables = [
        # --- projects ---
        """
        CREATE TABLE IF NOT EXISTS projects (
            id          VARCHAR(64)  NOT NULL,
            mode        VARCHAR(10)  NOT NULL COMMENT 'upload only',
            prompt      TEXT                  COMMENT 'Mode 2 prompt (nullable)',
            context     TEXT                  COMMENT 'User-provided context for captioning (optional)',
            zip_blob    LONGBLOB,
            language    VARCHAR(10)  NOT NULL,
            audio_vibe  VARCHAR(50)           COMMENT 'Selected audio vibe (calm, romantic, etc)',
            status      VARCHAR(30)  NOT NULL DEFAULT 'uploaded',
            created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,

        # --- images ---
        """
        CREATE TABLE IF NOT EXISTS images (
            id            INT          NOT NULL AUTO_INCREMENT,
            project_id    VARCHAR(64)  NOT NULL,
            filename      VARCHAR(255) NOT NULL,
            image_blob    LONGBLOB,
            display_order INT          NOT NULL DEFAULT 0,
            is_removed    TINYINT(1)   NOT NULL DEFAULT 0,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,

        # --- captions ---
        """
        CREATE TABLE IF NOT EXISTS captions (
            id                  INT          NOT NULL AUTO_INCREMENT,
            project_id          VARCHAR(64)  NOT NULL,
            image_filename      VARCHAR(255) NOT NULL,
            caption_en          TEXT,
            caption_translated  TEXT,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,

        # --- narrations ---
        """
        CREATE TABLE IF NOT EXISTS narrations (
            id              INT          NOT NULL AUTO_INCREMENT,
            project_id      VARCHAR(64)  NOT NULL,
            narration_text  LONGTEXT,
            narration_path  VARCHAR(255),
            narration_blob  LONGBLOB,
            language        VARCHAR(10),
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,

        # --- music ---
        """
        CREATE TABLE IF NOT EXISTS music (
            id           INT          NOT NULL AUTO_INCREMENT,
            project_id   VARCHAR(64)  NOT NULL,
            vibe         VARCHAR(50),
            source       VARCHAR(20)  COMMENT 'ai | library',
            music_path   VARCHAR(255),
            music_blob   LONGBLOB,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,

        # --- outputs ---
        """
        CREATE TABLE IF NOT EXISTS outputs (
            id           INT          NOT NULL AUTO_INCREMENT,
            project_id   VARCHAR(64)  NOT NULL,
            video_path   VARCHAR(255),
            video_blob   LONGBLOB,
            caption      TEXT,
            hashtags     TEXT,
            created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ]

    for sql in tables:
        cur.execute(sql)

    raw.commit()
    
    # Step 3: Upgrade existing tables
    try:
        cur.execute("ALTER TABLE projects ADD COLUMN zip_blob LONGBLOB AFTER context;")
        raw.commit()
    except mysql.connector.Error:
        pass
        
    try:
        cur.execute("ALTER TABLE projects ADD COLUMN audio_vibe VARCHAR(50) AFTER language;")
        raw.commit()
    except mysql.connector.Error:
        pass  # Column already exists
        
    try:
        cur.execute("ALTER TABLE outputs ADD COLUMN video_blob LONGBLOB AFTER video_path;")
        raw.commit()
    except mysql.connector.Error:
        pass  # Column already exists

    try:
        cur.execute("ALTER TABLE images ADD COLUMN image_blob LONGBLOB AFTER filename;")
        raw.commit()
    except mysql.connector.Error:
        pass
        
    try:
        cur.execute("ALTER TABLE narrations ADD COLUMN narration_blob LONGBLOB AFTER narration_path;")
        raw.commit()
    except mysql.connector.Error:
        pass

    try:
        cur.execute("ALTER TABLE music ADD COLUMN music_blob LONGBLOB AFTER music_path;")
        raw.commit()
    except mysql.connector.Error:
        pass

    cur.close()
    raw.close()
    print("[DB] Database and all tables ready.")

