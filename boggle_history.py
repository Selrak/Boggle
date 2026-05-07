import sqlite3
import json
import os
import uuid
from datetime import datetime

DB_NAME = "boggle_stats.db"

def set_db_name(debug=False):
    global DB_NAME
    DB_NAME = "boggle_stats_debug.db" if debug else "boggle_stats.db"
    if debug:
        print(f"[DEBUG] Database set to: {DB_NAME}")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            score INTEGER,
            max_score INTEGER,
            words_count INTEGER,
            max_words_count INTEGER,
            longest_word_found_len INTEGER,
            longest_word_possible_len INTEGER,
            found_lengths_json TEXT,
            possible_lengths_json TEXT,
            grid_string TEXT,
            found_words_json TEXT,
            has_paused INTEGER DEFAULT 0,
            playing_time INTEGER DEFAULT 180,
            is_finished INTEGER DEFAULT 1,
            guid TEXT UNIQUE
        )
    ''')
    # Migration
    try:
        cursor.execute('ALTER TABLE games ADD COLUMN has_paused INTEGER DEFAULT 0')
    except sqlite3.OperationalError: pass
    try:
        cursor.execute('ALTER TABLE games ADD COLUMN playing_time INTEGER DEFAULT 180')      
    except sqlite3.OperationalError: pass
    try:
        cursor.execute('ALTER TABLE games ADD COLUMN is_finished INTEGER DEFAULT 1')
    except sqlite3.OperationalError: pass
    try:
        cursor.execute('ALTER TABLE games ADD COLUMN guid TEXT')
        cursor.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_guid ON games(guid)')
    except sqlite3.OperationalError: pass

    # Backfill GUIDs for old entries
    cursor.execute('SELECT id FROM games WHERE guid IS NULL')
    rows = cursor.fetchall()
    for (rid,) in rows:
        new_guid = str(uuid.uuid4())
        cursor.execute('UPDATE games SET guid = ? WHERE id = ?', (new_guid, rid))

    conn.commit()
    conn.close()

def save_game(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Generate guid if not provided (e.g. from local game)
    g_guid = data.get('guid') or str(uuid.uuid4())

    cursor.execute('''
        INSERT OR IGNORE INTO games (
            score, max_score, words_count, max_words_count,
            longest_word_found_len, longest_word_possible_len,
            found_lengths_json, possible_lengths_json,
            grid_string, found_words_json, has_paused,
            playing_time, is_finished, guid
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['score'], data['max_score'], data['words_count'], data['max_words_count'],      
        data['longest_word_found_len'], data['longest_word_possible_len'],
        json.dumps(data['found_lengths']), json.dumps(data['possible_lengths']),
        data['grid_string'], json.dumps(data['found_words']),
        1 if data.get('has_paused') else 0,
        data.get('playing_time', 180),
        1 if data.get('is_finished') else 0,
        g_guid
    ))
    game_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return game_id
def get_history(only_finished=True):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if only_finished:
        cursor.execute('SELECT * FROM games WHERE is_finished = 1 AND playing_time >= 180 ORDER BY id ASC')
    else:
        cursor.execute('SELECT * FROM games ORDER BY id ASC')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_richness_bin(max_score):
    if max_score < 50: return "Aride"
    if max_score < 150: return "Fertile"
    return "Luxuriante"

def get_rankings(game_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Current game data
    cursor.execute('SELECT score, max_score FROM games WHERE id = ?', (game_id,))
    res = cursor.fetchone()
    if not res: return None
    current_score, max_score = res
    
    # Overall rank
    cursor.execute('SELECT COUNT(*) FROM games WHERE score > ?', (current_score,))
    rank_overall = cursor.fetchone()[0] + 1
    cursor.execute('SELECT COUNT(*) FROM games')
    total_games = cursor.fetchone()[0]
    
    # By richness
    richness = get_richness_bin(max_score)
    if richness == "Aride":
        cursor.execute('SELECT COUNT(*) FROM games WHERE score > ? AND max_score < 50', (current_score,))
    elif richness == "Fertile":
        cursor.execute('SELECT COUNT(*) FROM games WHERE score > ? AND max_score >= 50 AND max_score < 150', (current_score,))
    else:
        cursor.execute('SELECT COUNT(*) FROM games WHERE score > ? AND max_score >= 150', (current_score,))
    rank_richness = cursor.fetchone()[0] + 1
        
    conn.close()
    return {
        "overall_rank": rank_overall,
        "total_games": total_games,
        "richness": richness,
        "richness_rank": rank_richness
    }

if __name__ == "__main__":
    init_db()
