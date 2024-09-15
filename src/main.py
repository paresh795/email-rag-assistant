import asyncio
import logging
from src.email_integration import GmailMonitor
from src.knowledge_base import KnowledgeBase
from src.email_processing_pipeline import ProcessingPipeline
from config import USE_LOCAL_LLM

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    try:
        logging.info(f"Using {'Local LLM' if USE_LOCAL_LLM.lower() == 'true' else 'OpenAI'} for processing")
        gmail_monitor = GmailMonitor()
        knowledge_base = KnowledgeBase()
        processing_pipeline = ProcessingPipeline(knowledge_base)

        # Initial fetch of email history
        gmail_monitor.fetch_email_history()
        logging.info("Email history fetched and indexed")

        while True:
            logging.info("Checking for new emails...")
            new_emails = gmail_monitor.check_for_new_emails()

            for subject, body, message_id, sender in new_emails:
                logging.info(f"Processing email: {subject}")
                try:
                    final_response = processing_pipeline.process_email(subject, body, sender)
                    if final_response:
                        logging.info(f"Final response generated:\n{final_response[:500]}...")
                        
                        if len(final_response.split()) > 50:
                            draft_id = gmail_monitor.create_draft(message_id, final_response, sender, subject)
                            if draft_id:
                                gmail_monitor.apply_ai_drafted_label(message_id)
                                logging.info(f"Created draft for email: {subject} with draft ID: {draft_id}")
                                
                                # Verify draft creation
                                draft = gmail_monitor.service.users().drafts().get(userId='me', id=draft_id).execute()
                                logging.info(f"Verified draft: {draft}")
                            else:
                                logging.error(f"Failed to create draft for email: {subject}")
                        else:
                            logging.warning(f"Response too short for email: {subject}")
                    else:
                        logging.warning(f"No valid response generated for email: {subject}")
                except Exception as e:
                    logging.error(f"Error processing email {subject}: {str(e)}")
                    continue  # Continue processing other emails even if one fails

            # Update email history
            gmail_monitor.update_email_history()
            logging.info("Email history updated")

            logging.info("Waiting for 2 minutes before next check...")
            await asyncio.sleep(120)  # Wait for 2 minutes before checking again
    except Exception as e:
        logging.error(f"An error occurred in the main loop: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())