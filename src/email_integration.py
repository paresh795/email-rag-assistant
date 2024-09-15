import os
import pickle
import base64
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timezone, timedelta
from src.email_history import EmailHistory
from config import SCOPES, EMAIL_HISTORY_DAYS
from email.mime.text import MIMEText

class GmailMonitor:
    def __init__(self):
        self.service = self.get_gmail_service()
        self.ai_drafted_label_id = self.get_or_create_label('AI_Drafted')
        self.email_history = EmailHistory()

    def get_gmail_service(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'client_secret.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return build('gmail', 'v1', credentials=creds)

    def get_or_create_label(self, label_name):
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            for label in labels:
                if label['name'] == label_name:
                    return label['id']
            
            label = self.service.users().labels().create(userId='me', body={'name': label_name}).execute()
            return label['id']
        except Exception as e:
            logging.error(f"Error creating label: {e}")
            return None

    def get_last_history_id(self):
        if os.path.exists('last_history_id.txt'):
            with open('last_history_id.txt', 'r') as f:
                return int(f.read().strip())
        return None

    def save_last_history_id(self, history_id):
        with open('last_history_id.txt', 'w') as f:
            f.write(str(history_id))

    def check_for_new_emails(self):
        try:
            results = self.service.users().messages().list(userId='me', labelIds=['INBOX'], q='is:unread -label:AI_Drafted').execute()
            messages = results.get('messages', [])

            if not messages:
                logging.info("No new messages.")
                return []

            new_emails = []
            for message in messages:
                full_message = self.service.users().messages().get(userId='me', id=message['id']).execute()
                internal_date = int(full_message['internalDate']) / 1000  # Convert to seconds
                message_date = datetime.fromtimestamp(internal_date, tz=timezone.utc)
                
                if message_date.date() >= datetime.now(timezone.utc).date():
                    subject = self.get_subject(full_message)
                    body = self.get_body(full_message)
                    sender = self.get_sender_email(full_message)
                    new_emails.append((subject, body, full_message['id'], sender))

            return new_emails
        except Exception as e:
            logging.error(f"An error occurred while checking for new emails: {e}")
            return []

    def get_subject(self, message):
        headers = message['payload']['headers']
        return next((header['value'] for header in headers if header['name'].lower() == 'subject'), 'No Subject')

    def get_body(self, message):
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif message['payload']['mimeType'] == 'text/plain':
            return base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        return "No readable content"

    def get_sender_email(self, message):
        headers = message['payload']['headers']
        from_header = next((header['value'] for header in headers if header['name'].lower() == 'from'), '')
        return from_header.split('<')[-1].strip('>')

    def create_draft(self, message_id, response, sender, subject):
        try:
            message = self.service.users().messages().get(userId='me', id=message_id).execute()
            thread_id = message['threadId']
            
            mime_message = MIMEText(response)
            mime_message['to'] = sender
            mime_message['subject'] = f"Re: {subject}"
            
            raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode('utf-8')
            
            draft = self.service.users().drafts().create(userId='me', body={
                'message': {
                    'raw': raw_message,
                    'threadId': thread_id
                }
            }).execute()
            
            logging.info(f"Draft created successfully with ID: {draft['id']}")
            return draft['id']
        except Exception as e:
            logging.error(f"Error creating draft: {e}")
            return None

    def apply_ai_drafted_label(self, message_id):
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [self.ai_drafted_label_id]}
            ).execute()
            logging.info(f"Applied AI_Drafted label to message: {message_id}")
        except Exception as e:
            logging.error(f"Error applying AI_Drafted label: {e}")

    def fetch_email_history(self, days=30):
        try:
            query = f'after:{(datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")}'
            results = self.service.users().messages().list(userId='me', q=query, maxResults=100).execute()
            messages = results.get('messages', [])

            for message in messages:
                full_message = self.service.users().messages().get(userId='me', id=message['id']).execute()
                subject = self.get_subject(full_message)
                body = self.get_body(full_message)
                sender = self.get_sender_email(full_message)
                date = datetime.fromtimestamp(int(full_message['internalDate']) / 1000)
                
                self.email_history.add_email(
                    message['id'], sender, 'me', subject, body, date, full_message['threadId']
                )

            logging.info(f"Fetched and indexed {len(messages)} emails from the last {days} days")
        except Exception as e:
            logging.error(f"An error occurred while fetching email history: {e}")

    def update_email_history(self):
        last_history_id = self.get_last_history_id()
        if last_history_id:
            try:
                results = self.service.users().history().list(userId='me', startHistoryId=last_history_id).execute()
                history = results.get('history', [])
                
                for item in history:
                    for message_added in item.get('messagesAdded', []):
                        message = message_added['message']
                        full_message = self.service.users().messages().get(userId='me', id=message['id']).execute()
                        subject = self.get_subject(full_message)
                        body = self.get_body(full_message)
                        sender = self.get_sender_email(full_message)
                        date = datetime.fromtimestamp(int(full_message['internalDate']) / 1000)
                        
                        self.email_history.add_email(
                            message['id'], sender, 'me', subject, body, date, full_message['threadId']
                        )
                
                if 'historyId' in results:
                    self.save_last_history_id(results['historyId'])
                
                logging.info(f"Updated email history with {len(history)} new changes")
            except Exception as e:
                logging.error(f"An error occurred while updating email history: {e}")
        else:
            self.fetch_email_history(days=1)