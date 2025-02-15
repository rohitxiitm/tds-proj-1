from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
import tools.phaseA as phaseATools
import json
import logging
from utils import safe_read
from llm import ask_llm

from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


tools = [
    tool()
    for tool in [
        phaseATools.A1Tool,
        phaseATools.A2Tool,
        phaseATools.A3Tool,
        phaseATools.A4Tool,
        phaseATools.A5Tool,
        phaseATools.A6Tool,
        phaseATools.A7Tool,
        phaseATools.A8Tool,
        phaseATools.A9Tool,
        phaseATools.A10Tool,
    ]
]

logging.basicConfig(
    level=logging.INFO,  # Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Log format
)

# Create a logger
logger = logging.getLogger(__name__)


@app.get("/")
def home():
    return {
        "status": "success",
        "message": "Rohit Garg's (22f2001394@ds.study.iitm.ac.in) TDS project 1",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Placeholder for task execution
@app.post("/run")
async def run_task(task: str):
    try:
        print("Running Task : ", task)
        messages = (
            [
                {
                    "role": "system",
                    "content": "You are a function classifier that extracts structured parameters from queries.",
                },
                {"role": "user", "content": task},
            ],
        )
        tools_pool = tools
        response = ask_llm(messages, tools_pool)
        message = response.choices[0].message
        if not hasattr(message, "tool_calls") or not message.tool_calls:
            # If no tool calls, return the message content as error
            raise HTTPException(status_code=400, detail=message.content)

        tool_call = message.tool_calls[0].function
        task_code = tool_call.name
        arguments = tool_call.arguments

        for tool in tools_pool:
            if tool.name == task_code:
                logger.info(f"Calling Tool : {tool.name} with arguments {arguments}")
                tool_response = tool.run(**json.loads(arguments))
                logger.info(f"We got ToolResponse {tool_response}")
                return tool_response

    except Exception as e:
        print("error occurred", e)
        raise HTTPException(status_code=400, detail=str(e))


# Placeholder for file reading
@app.get("/read", response_class=PlainTextResponse)
async def read_file(path: str = Query(..., description="File path to read")):
    try:
        return safe_read(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
