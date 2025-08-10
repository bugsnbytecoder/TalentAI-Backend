import logging
import os
import fitz  # PyMuPDF
from rest_framework.response import Response
from rest_framework import status
import json
import time
from groq import Groq

from TalentAI import settings

def extract_pdf_text(attachment):
    """
    Extracts and summarizes text from a PDF file. Uses direct text extraction and falls back
    to OCR for scanned pages.

    Args:
        attachment (File): A Django InMemoryUploadedFile or File object.

    Returns:
        tuple:
            - full_text (str): The combined extracted text from all PDF pages.
            - summarized_text (str): Summarized version under 20k tokens.
    """
    try:
        # Read and load PDF content
        attachment.seek(0)
        raw_bytes = attachment.read()
        full_text = ""

        with fitz.open(stream=raw_bytes, filetype="pdf") as doc:
            for i, page in enumerate(doc):
                page_text = page.get_text("text")

                if page_text and page_text.strip():
                    full_text += page_text.strip() + "\n\n"

        return full_text

    except Exception as e:
        logging.error(f"[extract_pdf_text] Failed to extract from PDF: {e}")
        return ""
    
def create_response(success, message, body=None, status_code=status.HTTP_200_OK):
    try:
        response_data = {'success': success, 'message': message}
        if body is not None:
            response_data['body'] = body
        return Response(response_data, status=status_code)
    except Exception as e:
        error_message = f"Error creating response: {str(e)}"
        return Response({'success': False, 'message': error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

MAX_RETRIES = 3
RETRY_DELAY = 2 


def retry_groq_call(fn, *args, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logging.warning(f"Groq call failed (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise

def generate_response_with_groq(messages, response_format=None, model=None, max_completion_tokens=None, tools=None):
    try:
        model = model or os.getenv("GROQ_MODEL")
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("API key is missing. Please set the GROQ_API_KEY environment variable.")

        client = Groq(api_key=api_key)

        request_args = {
            "messages": messages,
            "model": model,
        }
        if max_completion_tokens:
            request_args["max_completion_tokens"] = max_completion_tokens
        if response_format and response_format == "json":
            request_args["response_format"] = {"type": "json_object"}
        if tools:
            request_args["tools"] = tools
        def groq_completion_request():
            return client.chat.completions.create(**request_args)

        chat_completion = retry_groq_call(groq_completion_request)
        response_content = chat_completion.choices[0].message.content
        if response_format and response_format == "json":
            response_content = json.loads(response_content)
        usage = chat_completion.usage
        return response_content, usage.model_dump()

    except ValueError as ve:
        print(f"ValueError: {ve}")
        return "There was an issue with your request.", None
    except Exception as e:
        print(f"An error occurred: {e}")
        return "An error occurred while processing your request.", None
