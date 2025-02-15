import os
import openai
from base import BaseTool
from dotenv import load_dotenv

load_dotenv()


api_key = os.getenv("AIPROXY_TOKEN")

# api_base = http://aiproxy.sanand.workers.dev/openai/v1
# model_name = "gpt-4o-mini"

api_base = "https://generativelanguage.googleapis.com/v1beta/openai"
model_name = "gemini-1.5-flash"

openai_client = openai.OpenAI(api_key=api_key, base_url=api_base)


def ask_llm(messages: list = [], tools: list[BaseTool] = []):
    response = openai_client.chat.completions.create(
        model=model_name,
        messages=messages,
        tools=[tool.to_llm_format() for tool in tools],
        tool_choice="auto",
    )
    return response
