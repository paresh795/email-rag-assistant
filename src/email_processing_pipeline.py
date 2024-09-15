import logging
from datetime import datetime
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from config import OPENAI_API_KEY, EMAIL_ADDRESS
from src.email_history import EmailHistory
from transformers import pipeline

class ProcessingPipeline:
    def __init__(self, knowledge_base):
        self.query_generator = QueryGenerationAgent()
        self.kb_searcher = KnowledgeBaseSearchAgent(knowledge_base)
        self.response_generator = ResponseGenerationAgent()
        self.email_history = EmailHistory()
        self.final_reviewer = FinalReviewAgent()
        self.email_summarizer = EmailSummarizer()

    def process_email(self, subject, body, sender):
        try:
            query = self.query_generator.generate_query(subject, body)
            logging.info(f"Generated query: {query}")

            kb_summary = self.kb_searcher.search_and_summarize(query)
            logging.info(f"Knowledge base summary: {kb_summary}")

            similar_emails = self.email_history.search_similar_emails(query)
            email_history_summary = self.email_summarizer.summarize_emails(similar_emails)
            logging.info(f"Email history summary: {email_history_summary}")

            initial_response = self.response_generator.generate_response(
                subject, body, kb_summary, email_history_summary, sender
            )
            
            final_response = self.final_reviewer.review_response(query, initial_response, kb_summary, email_history_summary)
            
            logging.info(f"Final response generated: {final_response[:500]}...")
            return final_response
        except Exception as e:
            logging.error(f"Error in processing pipeline: {e}")
            return None

class QueryGenerationAgent:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0.7, openai_api_key=OPENAI_API_KEY)
        self.prompt = ChatPromptTemplate.from_template(
            """You are an AI assistant specializing in analyzing emails and generating optimal queries for knowledge base searches. Your role is crucial in a multi-step email processing system.

            Given an email subject and body, your task is to generate a focused, relevant query that will be used to search a knowledge base for information to craft a response.

            Consider the following:
            1. Identify the main topic or question in the email.
            2. Focus on key terms that are likely to yield relevant results from the knowledge base.
            3. Phrase the query in a way that will maximize the chances of finding pertinent information.

            Email Subject: {subject}
            Email Body: {body}

            Generate an optimal search query based on this email:"""
        )

    def generate_query(self, subject, body):
        response = self.llm(self.prompt.format_messages(subject=subject, body=body))
        logging.info(f"Generated query: {response.content}")
        return response.content

class KnowledgeBaseSearchAgent:
    def __init__(self, knowledge_base):
        self.knowledge_base = knowledge_base
        self.llm = ChatOpenAI(temperature=0.7, openai_api_key=OPENAI_API_KEY)
        self.prompt = ChatPromptTemplate.from_template(
            """You are an AI assistant specializing in searching and synthesizing information from a knowledge base. Your role is to use a given query to search the knowledge base and provide relevant information for crafting an email response.

            Your task:
            1. Analyze the provided query and search results.
            2. Synthesize the most relevant information from the search results.
            3. Provide a concise summary of the key points that will be useful for generating an email response.

            Query: {query}

            Search Results:
            {search_results}

            Please provide a concise summary of the most relevant information:"""
        )

    def search_and_summarize(self, query):
        search_results = self.knowledge_base.query(query)
        search_results_text = "\n".join([doc.page_content for doc in search_results])
        response = self.llm(self.prompt.format_messages(query=query, search_results=search_results_text))
        logging.info(f"Knowledge base search summary: {response.content}")
        return response.content

class ResponseGenerationAgent:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0.7, openai_api_key=OPENAI_API_KEY)
        self.context_prompt = ChatPromptTemplate.from_template(
            """Summarize the context of this email conversation:
            Subject: {subject}
            Body: {body}
            Is this a new conversation or a continuation? Provide a concise summary.
            """
        )
        self.response_prompt = ChatPromptTemplate.from_template(
            """You are an AI assistant with email address {ai_email}. Your role is to create professional email responses.

            Consider the following when crafting your response:
            1. Maintain a professional and helpful tone.
            2. Address all points raised in the original email.
            3. Incorporate relevant information from the knowledge base summary and email history.
            4. Ensure the response is clear, concise, and well-structured.
            5. Use Markdown formatting for headings and important points.

            Original Email Subject: {subject}
            Original Email Body: {body}
            Sender's Email: {sender_email}
            Knowledge Base Summary: {kb_summary}
            Email History Summary: {email_history_summary}

            Please generate a professional email response following this exact structure:

            # Context Summary
            [Provide a brief summary of the email context]

            # Knowledge Base Insights
            [List key insights from the knowledge base, with citations]

            # Relevant Email History
            {email_history_summary}

            # Draft Response
            [Generate the actual email response here]

            Generated response:"""
        )

    def generate_response(self, subject, body, kb_summary, email_history_summary, sender_email):
        context_summary = self.llm(self.context_prompt.format_messages(
            subject=subject,
            body=body
        )).content

        response = self.llm(self.response_prompt.format_messages(
            subject=subject, 
            body=body, 
            kb_summary=kb_summary,
            email_history_summary=email_history_summary,
            ai_email=EMAIL_ADDRESS, 
            sender_email=sender_email
        )).content

        return response

class FinalReviewAgent:
    def __init__(self):
        self.llm = ChatOpenAI(temperature=0.3, openai_api_key=OPENAI_API_KEY)
        self.prompt = ChatPromptTemplate.from_template(
            """You are an AI assistant responsible for reviewing and refining email responses. Your task is to ensure the response is professional, accurate, and includes all necessary information.

            The response should strictly maintain the following structure with Markdown formatting:
            # Context Summary
            # Knowledge Base Insights (with citations)
            # Relevant Email History
            # Draft Response

            Original query: {query}
            Initial response:
            {initial_response}

            Please review and refine the response, ensuring it maintains the exact structure with Markdown formatting and includes all relevant information. The final response should be concise but informative.

            Refined response:"""
        )

    def review_response(self, query, initial_response, kb_summary, email_history_summary):
        response = self.llm(self.prompt.format_messages(
            query=query,
            initial_response=initial_response
        ))
        return response.content

class EmailSummarizer:
    def __init__(self):
        self.summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

    def summarize_emails(self, emails, max_length=50):
        summaries = []
        for email in emails[:3]:  # Limit to top 3 emails
            date = email.get('date', datetime.now())
            if isinstance(date, str):
                try:
                    date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    date = datetime.now()
            formatted_date = date.strftime("%Y-%m-%d %H:%M")
            sender = email.get('sender', 'Unknown')
            subject = email.get('subject', 'No Subject')
            body = email.get('body', '')
            summary = self.summarizer(body, max_length=max_length, min_length=20, do_sample=False)[0]['summary_text']
            summaries.append(f"**Date:** {formatted_date}\n**Sender:** {sender}\n**Subject:** {subject}\n**Summary:** {summary}\n")
        return "\n".join(summaries)