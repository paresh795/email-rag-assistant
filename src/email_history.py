import os
import sqlite3
import logging
from datetime import datetime, timedelta
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from config import OPENAI_API_KEY

class EmailHistory:
    def __init__(self, db_path='email_history.db', vector_store_path='email_vectors'):
        self.db_path = db_path
        self.vector_store_path = vector_store_path
        self.embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
        self.setup_database()
        self.load_or_create_vector_store()

    def setup_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emails (
                id TEXT PRIMARY KEY,
                sender TEXT,
                recipient TEXT,
                subject TEXT,
                body TEXT,
                date DATETIME,
                thread_id TEXT,
                vector_id TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def load_or_create_vector_store(self):
        if os.path.exists(self.vector_store_path):
            self.vector_store = FAISS.load_local(self.vector_store_path, self.embeddings)
        else:
            self.vector_store = FAISS.from_texts([""], self.embeddings)

    def add_email(self, email_id, sender, recipient, subject, body, date, thread_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM emails WHERE id = ?", (email_id,))
        if cursor.fetchone():
            conn.close()
            return

        # Add to vector store
        vector = self.vector_store.add_texts([body], metadatas=[{"email_id": email_id}])
        vector_id = vector[0]

        # Add to SQLite database
        cursor.execute('''
            INSERT INTO emails (id, sender, recipient, subject, body, date, thread_id, vector_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (email_id, sender, recipient, subject, body, date, thread_id, vector_id))
        
        conn.commit()
        conn.close()

    def search_similar_emails(self, query, k=3):
        results = self.vector_store.similarity_search_with_score(query, k=k)
        similar_emails = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for doc, score in results:
            email_id = doc.metadata.get('email_id')
            if email_id:
                cursor.execute("SELECT * FROM emails WHERE id = ?", (email_id,))
                email_data = cursor.fetchone()
                if email_data:
                    similar_emails.append({
                        'id': email_data[0],
                        'sender': email_data[1],
                        'recipient': email_data[2],
                        'subject': email_data[3],
                        'body': email_data[4],
                        'date': email_data[5],
                        'thread_id': email_data[6],
                        'similarity_score': score
                    })
        conn.close()
        return similar_emails

    def save_vector_store(self):
        self.vector_store.save_local(self.vector_store_path)

    def get_recent_emails(self, days=30):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        date_threshold = datetime.now() - timedelta(days=days)
        cursor.execute("SELECT * FROM emails WHERE date > ?", (date_threshold,))
        recent_emails = cursor.fetchall()
        conn.close()
        return recent_emails
