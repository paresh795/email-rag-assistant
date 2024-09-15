import json
import os

class ProcessedEmails:
    def __init__(self, file_path='processed_emails.json'):
        self.file_path = file_path
        self.processed_ids = self.load_processed_ids()

    def load_processed_ids(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                return set(json.load(f))
        return set()

    def save_processed_ids(self):
        with open(self.file_path, 'w') as f:
            json.dump(list(self.processed_ids), f)

    def add_processed_email(self, email_id):
        self.processed_ids.add(email_id)
        self.save_processed_ids()

    def is_processed(self, email_id):
        return email_id in self.processed_ids
