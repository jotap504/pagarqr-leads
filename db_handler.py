import sqlite3
import pandas as pd
import os
from datetime import datetime

class Database:
    def __init__(self, db_path='data/leads.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.create_table()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def create_table(self):
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company TEXT,
                    website TEXT,
                    email TEXT,
                    whatsapp TEXT,
                    niche TEXT,
                    source TEXT,
                    status TEXT DEFAULT 'Pendiente',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

    def insert_lead(self, lead_data):
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO leads (company, website, email, whatsapp, niche, source, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                lead_data.get('company'),
                lead_data.get('website'),
                lead_data.get('email'),
                lead_data.get('whatsapp'),
                lead_data.get('niche'),
                lead_data.get('source'),
                lead_data.get('status', 'Pendiente'),
                lead_data.get('notes')
            ))

    def get_all_leads(self):
        with self.get_connection() as conn:
            return pd.read_sql_query("SELECT * FROM leads ORDER BY created_at DESC", conn)

    def update_lead_status(self, lead_id, status):
        with self.get_connection() as conn:
            conn.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))

    def update_lead_notes(self, lead_id, notes):
        with self.get_connection() as conn:
            conn.execute("UPDATE leads SET notes = ? WHERE id = ?", (notes, lead_id))

    def delete_lead(self, lead_id):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
