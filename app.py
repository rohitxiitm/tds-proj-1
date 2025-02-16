import json
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
logging.basicConfig(
    level=logging.INFO,  # Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Log format
)

# Create a logger
logger = logging.getLogger(__name__)

from utils import safe_read
from llm import ask_llm
import tools.phaseA as phaseATools
import tools.phaseB as phaseBTools

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
        phaseBTools.CodeRunnerTool,
    ]
]


@app.get("/", response_class=PlainTextResponse)
def home():
    return PlainTextResponse(
        {
            "status": "success",
            "message": "Rohit Garg's (22f2001394@ds.study.iitm.ac.in) TDS project 1",
        }
    )


@app.get("/health", response_class=PlainTextResponse)
def health_check():
    return PlainTextResponse({"status": "healthy"})


# Placeholder for task execution
@app.post("/run", response_class=PlainTextResponse)
async def run_task(task: str):
    try:
        logger.info(f"Running Task: {task}")
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a function classifier that analyzes user queries and selects "
                    "the appropriate tool from available options. For each query:\n"
                    "1. Understand the user's request\n"
                    "2. Match it to the most suitable tool\n"
                    "3. Extract required parameters accurately\n\n"
                    "For SQL-related tasks specifically:\n"
                    "- Construct precise queries without additional text\n"
                    "- Ensure query produces exactly the requested output"
                    "If no relevant tool is found use code runner tool to execute that task"
                ),
            },
            {"role": "user", "content": task},
        ]
        tools_pool = tools
        response = ask_llm(messages, tools_pool)
        message = response.choices[0].message
        if not hasattr(message, "tool_calls") or not message.tool_calls:
            # If no tool calls, return the message content as error
            raise HTTPException(status_code=400, detail=str(message.content))

        tool_call = message.tool_calls[0].function
        task_code = tool_call.name
        arguments = tool_call.arguments

        for tool in tools_pool:
            if tool.name == task_code:
                logger.info(f"Calling Tool : {tool.name} with arguments {arguments}")
                tool_response = tool.run(**json.loads(arguments))
                logger.info(f"We got ToolResponse {tool_response}")
                return PlainTextResponse(str(tool_response.__dict__))

    except Exception as e:
        logger.error("error occurred", exc_info=e)
        raise HTTPException(status_code=400, detail=str(e))


# Placeholder for file reading
@app.get("/read", response_class=PlainTextResponse)
async def read_file(path: str = Query(..., description="File path to read")):
    try:
        return safe_read(path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error : {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
