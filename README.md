# TDS Project 1 – LLM-Powered Data Science Tools

## Project Description
**TDS Project 1** is an AI-driven tool orchestration system built with FastAPI. It uses a Large Language Model (LLM) to analyze natural language queries and route them to the appropriate data-processing "tool" (function) for execution. The project includes a suite of tools (e.g. web scraping, data analysis, database queries, etc.), each implementing a specific functionality. The LLM acts as a **function classifier** – it interprets the user’s request, selects the most suitable tool, and extracts the needed parameters for that tool. If no predefined tool is applicable, the system falls back to a general-purpose code execution tool (the **CodeRunner** tool) to handle the request. This approach allows natural language inputs to trigger complex operations through the appropriate tool, with the LLM managing the decision of **which** tool to use and how to use it.

## Installation & Setup
### Prerequisites
- **Python 3.12+** (the project is designed to run on Python 3.12, including in Docker).
- **Virtual environment (recommended)** to isolate dependencies.
- **LLM API credentials** (e.g., AI_PROXY API key or Google PaLM API token).

### Steps
1. **Clone the Repository**
   ```bash
   git clone https://github.com/rohitxiitm/tds-proj-1.git
   cd tds-proj-1
   ```
2. **Install Dependencies**
   ```bash
   pip install -e .
   ```
3. **Configure Environment Variables**
   Create a `.env` file and set the required API credentials:
   ```ini
   AIPROXY_TOKEN=your_proxy_token
   GEMINI_TOKEN=your_gemini_key
   ```
4. **Run the API Server**
   ```bash
   uvicorn app:app --reload
   ```
5. **(Optional) Docker Setup**
   ```bash
   docker build -t tds-proj-1 .
   docker run -p 8000:8000 tds-proj-1
   ```

## Usage
### API Endpoints
- **GET `/health`** – Returns `{ "status": "healthy" }` to indicate service availability.
- **POST `/run`** – Executes a task using an LLM-selected tool.
  ```bash
  curl -X POST "http://localhost:8000/run" -H "Content-Type: application/json" \
       -d '{"task": "Fetch the latest data from the website and compute the total sales."}'
  ```
  The LLM will decide which tool to use and return the processed output.
- **GET `/read?path=<file_path>`** – Reads and returns contents of a local file.

## Project Architecture
### Key Components
- **`app.py` (FastAPI App)** – Defines API routes and handles requests, LLM interactions, and tool execution.
- **`llm.py` (LLM Interface)** – Calls the OpenAI/Gemini API, formats queries, and determines tool usage.
- **`base.py` (Tool Base Class)** – Defines the `BaseTool` abstract class that all tools inherit from.
- **`tools/` (Tool Implementations)** – Individual tools for data processing, web scraping, SQL queries, etc.
- **`constants.py` & `utils.py`** – Stores reusable constants and helper functions.
- **`Dockerfile`** – Containerized setup for consistent deployment.

### How It Works
1. The **LLM analyzes** the user’s request.
2. It selects the **most suitable tool** from the available options.
3. The **FastAPI server executes** the tool and returns results.
4. If no predefined tool applies, the system uses the **CodeRunnerTool** for custom execution.

## Summary
This project enables **natural language-driven data analysis** using an LLM to intelligently select and execute tools. The modular design allows easy addition of new tools, making the system adaptable and scalable.

