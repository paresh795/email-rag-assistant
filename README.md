# Email RAG Assistant

This project implements an AI-powered email assistant that monitors a Gmail inbox, processes new emails, and generates draft responses using a Retrieval-Augmented Generation (RAG) approach.

## Features

- Monitors Gmail inbox for new emails
- Processes emails using a multi-agent system:
  1. Query Generation Agent
  2. Knowledge Base Search Agent
  3. Response Generation Agent
  4. Final Review Agent
- Generates draft responses based on email content and knowledge base
- Applies an "AI_Drafted" label to processed emails

## Prerequisites

- Python 3.7+
- Gmail account
- Google Cloud Platform project with Gmail API enabled

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/email-rag-assistant.git
   cd email-rag-assistant
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv email_rag_env
   source email_rag_env/bin/activate  # On Windows, use `email_rag_env\Scripts\activate`
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt

   ```
        
   For a full reproducible environment, you can use:
      ```bash
      pip install -r requirements-full.txt
      ```

4. Set up Gmail API:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Gmail API for your project
   - Create OAuth 2.0 credentials (Desktop app)
   - Download the client configuration and save it as `client_secret.json` in the project root

5. Create a `.env` file in the project root and add the following:
   ```bash
   OPENAI_API_KEY=your_openai_api_key
   USE_LOCAL_LLM=false
   EMAIL_HISTORY_DAYS=30
   ```

## Usage

1. Run the main script:
   ```bash
   python -m src.main
   ```

2. On first run, you'll be prompted to authorize the application. Follow the URL provided in the console to grant access to your Gmail account.

3. The script will start monitoring your inbox for new emails and process them automatically.

## Customization

- To modify the knowledge base, update the documents in the `knowledge_base` directory.
- Adjust the email processing pipeline in `src/email_processing_pipeline.py`.
- Modify the Gmail monitoring settings in `src/email_integration.py`.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
