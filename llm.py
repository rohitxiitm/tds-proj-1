import os
import openai
from base import BaseTool
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

api_key = os.getenv("GEMINI_TOKEN") or os.getenv("AIPROXY_TOKEN")

if os.getenv("GEMINI_TOKEN"):
    api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
    model_name = "gemini-1.5-flash"
    embedding_model = "text-embedding-004"
else:
    api_base = "http://aiproxy.sanand.workers.dev/openai/v1"
    model_name = "gpt-4o-mini"
    embedding_model = "text-embedding-3-small"

logger.info(
    f"Using {model_name} and {embedding_model} via {'Gemini' if os.getenv('GEMINI_TOKEN') else 'OpenAI Proxy'}"
)

openai_client = openai.OpenAI(api_key=api_key, base_url=api_base)


def ask_llm(messages: list = [], tools: list[BaseTool] = []):
    kwargs = {
        "model": model_name,
        "messages": messages,
    }

    if tools:
        kwargs["tools"] = [tool.to_llm_format() for tool in tools]
        kwargs["tool_choice"] = "auto"

    response = openai_client.chat.completions.create(**kwargs)
    return response


def get_embedding(inputs: list):
    response = openai_client.embeddings.create(input=inputs, model=embedding_model)
    return response
