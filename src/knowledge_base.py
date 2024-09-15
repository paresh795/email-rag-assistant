import logging
from langchain.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from config import DOCUMENTS_DIR, OPENAI_API_KEY, LOCAL_LLM_BASE_URL, USE_LOCAL_LLM
import os
from sentence_transformers import SentenceTransformer, CrossEncoder, util
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class KnowledgeBase:
    def __init__(self):
        self.documents = []
        self.texts = []
        self.bi_encoder = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')
        self.tfidf_vectorizer = TfidfVectorizer()
        self.document_embeddings = None
        self.tfidf_matrix = None
        self.load_documents()
        self.index_documents()

    def load_documents(self):
        if not os.path.exists(DOCUMENTS_DIR):
            logging.warning(f"Documents directory does not exist: {DOCUMENTS_DIR}")
            return

        logging.info(f"Attempting to load documents from: {DOCUMENTS_DIR}")

        pdf_loader = DirectoryLoader(DOCUMENTS_DIR, glob="**/*.pdf", loader_cls=PyPDFLoader)
        txt_loader = DirectoryLoader(DOCUMENTS_DIR, glob="**/*.txt", loader_cls=TextLoader)

        pdf_docs = pdf_loader.load()
        txt_docs = txt_loader.load()

        self.documents = pdf_docs + txt_docs

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.texts = text_splitter.split_documents(self.documents)

        logging.info(f"Loaded {len(pdf_docs)} PDF documents")
        logging.info(f"Loaded {len(txt_docs)} TXT documents")
        logging.info(f"Total loaded documents: {len(self.documents)}")
        logging.info(f"Total text chunks: {len(self.texts)}")

    def index_documents(self):
        if not self.texts:
            logging.warning("No documents to index.")
            return

        document_contents = [doc.page_content for doc in self.texts]
        self.document_embeddings = self.bi_encoder.encode(document_contents, convert_to_tensor=True)
        self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(document_contents)

    def search(self, query, top_k=5):
        if not self.texts:
            logging.warning("No documents in the knowledge base. Unable to perform search.")
            return []

        query_embedding = self.bi_encoder.encode(query, convert_to_tensor=True)
        query_tfidf = self.tfidf_vectorizer.transform([query])

        # Semantic search
        semantic_scores = util.pytorch_cos_sim(query_embedding, self.document_embeddings)[0]
        semantic_top_k = semantic_scores.argsort(descending=True)[:top_k]

        # TF-IDF search
        tfidf_scores = cosine_similarity(query_tfidf, self.tfidf_matrix)[0]
        tfidf_top_k = tfidf_scores.argsort()[::-1][:top_k]

        # Combine results
        combined_indices = list(set(semantic_top_k.tolist() + tfidf_top_k.tolist()))
        combined_scores = [max(semantic_scores[i], tfidf_scores[i]) for i in combined_indices]

        # Sort by combined scores
        sorted_indices = [x for _, x in sorted(zip(combined_scores, combined_indices), reverse=True)]

        return [self.texts[i] for i in sorted_indices[:top_k]]

    def query(self, question, k=3):
        return self.search(question, top_k=k)