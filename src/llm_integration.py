import logging
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from config import OPENAI_API_KEY

class LLMIntegration:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in the environment variables")
        self.llm = ChatOpenAI(temperature=0.7, openai_api_key=OPENAI_API_KEY)
        self.prompt = PromptTemplate(
            input_variables=["email_subject", "email_body", "context"],
            template="""
            Given the following email and context from our knowledge base, generate a response:

            Email Subject: {email_subject}
            Email Body: {email_body}

            Context from Knowledge Base:
            {context}

            Please generate a professional and helpful response:
            """
        )
        self.chain = LLMChain(llm=self.llm, prompt=self.prompt)

    def generate_response(self, email_subject, email_body, context):
        try:
            return self.chain.run(email_subject=email_subject, email_body=email_body, context=context)
        except Exception as e:
            logging.error(f"Error generating response: {e}")
            return "I apologize, but I'm unable to generate a response at this time. Please try again later."