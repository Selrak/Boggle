import sqlite3
import json
import os
from datetime import datetime

DB_NAME = "boggle_stats.db"

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
            found_words_json TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_game(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO games (
            score, max_score, words_count, max_words_count,
            longest_word_found_len, longest_word_possible_len,
            found_lengths_json, possible_lengths_json,
            grid_string, found_words_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['score'], data['max_score'], data['words_count'], data['max_words_count'],
        data['longest_word_found_len'], data['longest_word_possible_len'],
        json.dumps(data['found_lengths']), json.dumps(data['possible_lengths']),
        data['grid_string'], json.dumps(data['found_words'])
    ))
    game_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return game_id

def get_history():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games ORDER BY id ASC')
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_richness_bin(max_score):
    if max_score < 50: return "Poor"
    if max_score < 150: return "Average"
    return "Rich"

def get_rankings(game_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Current game data
    cursor.execute('SELECT score, max_score FROM games WHERE id = ?', (game_id,))
    res = cursor.fetchone()
    if not res: return None
    current_score, max_score = res
    
    # Overall rank
    cursor.execute('SELECT COUNT(*) + 1 FROM games WHERE score > ?', (current_score,))
    overall_rank = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM games')
    total_games = cursor.fetchone()[0]
    
    # Binned rank
    richness = get_richness_bin(max_score)
    if richness == "Poor":
        cursor.execute('SELECT COUNT(*) + 1 FROM games WHERE score > ? AND max_score < 50', (current_score,))
        cursor.execute('SELECT COUNT(*) FROM games WHERE max_score < 50') # wait, I need to fetch both
    # Refactoring ranking query to be more robust
    
    # Overall
    cursor.execute('SELECT COUNT(*) FROM games WHERE score > ?', (current_score,))
    rank_overall = cursor.fetchone()[0] + 1
    
    # By richness
    if max_score < 50:
        cursor.execute('SELECT COUNT(*) FROM games WHERE score > ? AND max_score < 50', (current_score,))
        rank_richness = cursor.fetchone()[0] + 1
    elif max_score < 150:
        cursor.execute('SELECT COUNT(*) FROM games WHERE score > ? AND max_score >= 50 AND max_score < 150', (current_score,))
        rank_richness = cursor.fetchone()[0] + 1
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
