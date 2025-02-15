from abc import ABC, abstractmethod
import subprocess
from dateutil.parser import parse
import json
import os
import requests
from scipy.spatial.distance import cosine
import sqlite3
import constants
from dotenv import load_dotenv
from pathlib import Path
import logging

from base import BaseTool, ToolResponse, ToolStatus
from utils import safe_path, safe_read, safe_write

load_dotenv()

logger = logging.getLogger(__name__)


class A1Tool(BaseTool):
    name = "A1"
    description = (
        "Run a Python script from a given URL, passing an email as the argument."
    )
    parameters = {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "Email argument for the python script",
                "default": constants.DEFAULT_EMAIL,
            },
            "script_url": {
                "type": "string",
                "description": f"Url to python script needs to be executed if not provided, use this {constants.DATAGEN_SCRIPT_URL}",
                "default": constants.DATAGEN_SCRIPT_URL,
            },
        },
        "required": ["script_url", "email"],
    }

    def run(self, script_url, email):
        logger.info(f"Runnig tool {self.name}")

        save_at = safe_path("/data")
        logger.info(f"Saving data at {save_at}")
        try:
            cmd = ["uv", "run", script_url, email, "--root", save_at]
            logger.info(f"Running cmd  {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                return ToolResponse(status=ToolStatus.ERROR, message=f"Error: {stderr}")
            return ToolResponse(status=ToolStatus.SUCCESS, data={"output": stdout})
        except Exception as e:
            return ToolResponse(status=ToolStatus.ERROR, message=f"Error: {e}")


class A2Tool(BaseTool):
    agent_name = "A2"
    description = "Format a markdown file using a specified version of Prettier."
    parameters = {
        "type": "object",
        "properties": {
            "prettier_version": {
                "type": "string",
                "description": "Version of prettier to use (stricly use x.y.z format)",
                "default": "3.4.2",
            },
            "filename": {
                "type": "string",
                "description": "Path to markdown file to format",
                "default": "/data/format.md",
            },
        },
        "required": ["filename"],
    }

    def run(self, prettier_version="3.4.2", filename="/data/format.md"):
        logger.info(f"Runnig tool {self.name}")

        # Validate inputs
        safe_filename = safe_path(filename)
        if not os.path.exists(safe_filename):
            return ToolResponse(
                status=ToolStatus.ERROR, message=f"File {filename} does not exist"
            )

        # Construct prettier version string
        prettier_pkg = f"prettier@{prettier_version}"

        cmd = ["npx", "--yes", prettier_pkg, "--write", safe_filename]

        logger.info(f"Running cmd  {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            return ToolResponse(
                status=ToolStatus.SUCCESS,
                message="File formatted successfully",
                data={"output": result.stdout},
            )
        except subprocess.CalledProcessError as e:
            return ToolResponse(
                status=ToolStatus.ERROR, message=f"Prettier failed: {e.stderr}"
            )
        except Exception as e:
            return ToolResponse(
                status=ToolStatus.ERROR, message=f"Unexpected error: {str(e)}"
            )


class A3Tool(BaseTool):
    agent_name = "A3"
    description = (
        "Count the number of occurrences of a specific weekday in a date file. "
        "Weekday numbers are: 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, "
        "4=Friday, 5=Saturday, 6=Sunday"
    )
    parameters = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Input file containing dates",
                "default": "/data/dates.txt",
            },
            "targetfile": {
                "type": "string",
                "description": "Output file to write count to",
                "default": "/data/output.txt",
            },
            "weekday": {
                "type": "integer",
                "description": "Day of week (0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday)",
            },
        },
        "required": ["weekday"],
    }

    def run(
        self,
        weekday,
        filename="/data/dates.txt",
        targetfile="/data/output.txt",
    ):
        logger.info(f"Running tool {self.name}")

        try:
            # Validate inputs
            if not os.path.exists(safe_path(filename)):
                return ToolResponse(
                    status=ToolStatus.ERROR,
                    message=f"Input file {filename} does not exist",
                )

            weekday = int(weekday)
            if not 0 <= weekday <= 6:
                return ToolResponse(
                    status=ToolStatus.ERROR, message="Weekday must be between 0 and 6"
                )

            # Process dates
            dates = safe_read(filename).splitlines()
            weekday_count = 0
            for date in dates:
                parsed_date = parse(date)
                if parsed_date.weekday() == weekday:
                    weekday_count += 1

            # Write result
            safe_write(targetfile, str(weekday_count))

            return ToolResponse(
                status=ToolStatus.SUCCESS, data={"count": weekday_count}
            )

        except ValueError as e:
            return ToolResponse(
                status=ToolStatus.ERROR, message=f"Invalid date format: {str(e)}"
            )
        except Exception as e:
            return ToolResponse(
                status=ToolStatus.ERROR, message=f"Unexpected error: {str(e)}"
            )


class A4Tool(BaseTool):
    agent_name = "A4"
    description = (
        "Sort a JSON contacts file and save the sorted version to a target file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Input JSON file containing contacts",
            },
            "targetfile": {
                "type": "string",
                "description": "Output JSON file to write sorted contacts to",
            },
        },
        "required": ["filename", "targetfile"],
    }

    def run(
        self, filename="/data/contacts.json", targetfile="/data/contacts-sorted.json"
    ):
        try:
            contacts = json.loads(safe_read(filename))
            sorted_contacts = sorted(
                contacts, key=lambda x: (x["last_name"], x["first_name"])
            )
            safe_write(targetfile, json.dumps(sorted_contacts, indent=4))
            return ToolResponse(status=ToolStatus.SUCCESS)
        except Exception as e:
            return ToolResponse(status=ToolStatus.ERROR, message=str(e))


class A5Tool(BaseTool):
    agent_name = "A5"
    description = "Retrieve the most recent log files from a directory and save their content to an output file."
    parameters = {
        "type": "object",
        "properties": {
            "log_dir_path": {
                "type": "string",
                "description": "Directory containing log files",
                "default": "/data/logs",
            },
            "output_file_path": {
                "type": "string",
                "description": "Output text file to write log contents to",
                "default": "/data/logs-recent.txt",
            },
            "num_files": {
                "type": "integer",
                "description": "Number of most recent files to process",
                "minimum": 1,
                "default": 10,
            },
        },
        "required": ["log_dir_path", "output_file_path", "num_files"],
    }

    def run(
        self,
        log_dir_path="/data/logs",
        output_file_path="/data/logs-recent.txt",
        num_files=10,
    ):
        try:
            log_dir = Path(safe_path(log_dir_path))
            output_file = Path(safe_path(output_file_path))

            log_files = sorted(
                log_dir.glob("*.log"), key=os.path.getmtime, reverse=True
            )[:num_files]

            with output_file.open("w") as f_out:
                for log_file in log_files:
                    with log_file.open("r") as f_in:
                        first_line = f_in.readline().strip()
                        f_out.write(f"{first_line}\n")
            return ToolResponse(status=ToolStatus.SUCCESS)
        except Exception as e:
            return ToolResponse(status=ToolStatus.ERROR, message=str(e))


class A6Tool(BaseTool):
    agent_name = "A6"
    description = (
        "Generate an index of documents from a directory and save it as a JSON file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "doc_dir_path": {
                "type": "string",
                "description": "Directory containing documents to index",
                "default": "/data/docs",
            },
            "output_file_path": {
                "type": "string",
                "description": "Output JSON file to write index to",
                "default": "/data/docs/index.json",
            },
        },
        "required": ["doc_dir_path", "output_file_path"],
    }

    def run(self, doc_dir_path="/data/docs", output_file_path="/data/docs/index.json"):
        try:
            safe_doc_dir = safe_path(doc_dir_path)
            index_data = {}
            for root, _, files in os.walk(safe_doc_dir):
                for file in files:
                    if file.endswith(".md"):
                        file_path = os.path.join(root, file)
                        content = safe_read(file_path, encoding="utf-8")
                        for line in content.splitlines():
                            if line.startswith("# "):
                                title = line[2:].strip()
                                relative_path = os.path.relpath(
                                    file_path, safe_doc_dir
                                ).replace("\\", "/")
                                index_data[relative_path] = title
                                break

            safe_write(
                output_file_path, json.dumps(index_data, indent=4), encoding="utf-8"
            )
            return ToolResponse(status=ToolStatus.SUCCESS)
        except Exception as e:
            return ToolResponse(status=ToolStatus.ERROR, message=str(e))


class A7Tool(BaseTool):
    agent_name = "A7"
    description = "Extract the email address from a text file and save it to an output file."
    parameters = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Input text file containing email content",
                "default": "/data/email.txt",
            },
            "output_file": {
                "type": "string",
                "description": "Output text file to write sender's email to",
                "default": "/data/email-sender.txt",
            },
        },
        "required": ["filename", "output_file"],
    }

    def run(self, filename="/data/email.txt", output_file="/data/email-sender.txt"):
        try:
            email_content = safe_read(filename).splitlines()

            sender_email = "rohitgxrg@gmail.com"
            for line in email_content:
                if "From" == line[:4]:
                    sender_email = (
                        (line.strip().split(" ")[-1]).replace("<", "").replace(">", "")
                    )
                    break

            safe_write(output_file, sender_email)
            return ToolResponse(status=ToolStatus.SUCCESS)
        except Exception as e:
            return ToolResponse(status=ToolStatus.ERROR, message=str(e))


class A8Tool(BaseTool):
    agent_name = "A8"
    description = (
        "Generate an image representation of credit card details from a text file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Output text file to write credit card number to",
                "default": "/data/credit-card.txt",
            },
            "image_path": {
                "type": "string",
                "description": "Input PNG image containing credit card details",
                "default": "/data/credit-card.png",
            },
        },
        "required": ["filename", "image_path"],
    }

    def run(self, filename="/data/credit_card.txt", image_path="/data/credit_card.png"):
        try:
            body = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract the 8+ digit number with spaces "
                                "after every 4 digits",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,"
                                    f"{png_to_base64(safe_path(image_path))}"
                                },
                            },
                        ],
                    }
                ],
            }

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {AIPROXY_TOKEN}",
            }

            response = requests.post(
                "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
                headers=headers,
                data=json.dumps(body),
            )

            result = response.json()
            card_number = result["choices"][0]["message"]["content"].replace(" ", "")

            safe_write(filename, card_number)
            return ToolResponse(status=ToolStatus.SUCCESS)
        except Exception as e:
            return ToolResponse(status=ToolStatus.ERROR, message=str(e))


class A9Tool(BaseTool):
    agent_name = "A9"
    description = (
        "Find similar comments from a text file and save them to an output file."
    )
    parameters = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Input text file containing comments",
                "default": "/data/comments.txt",
            },
            "output_filename": {
                "type": "string",
                "description": "Output text file to write similar comments to",
                "default": "/data/comments-similar.txt",
            },
        },
        "required": ["filename", "output_filename"],
    }

    def run(
        self,
        filename="/data/comments.txt",
        output_filename="/data/comments-similar.txt",
    ):
        try:
            comments = safe_read(filename).splitlines()

            embeddings = [get_embedding(comment) for comment in comments]

            min_distance = float("inf")
            most_similar = (None, None)

            for i in range(len(comments)):
                for j in range(i + 1, len(comments)):
                    distance = cosine(embeddings[i], embeddings[j])
                    if distance < min_distance:
                        min_distance = distance
                        most_similar = (comments[i], comments[j])

            safe_write(output_filename, most_similar[0] + "\n" + most_similar[1] + "\n")
            return ToolResponse(status=ToolStatus.SUCCESS)
        except Exception as e:
            return ToolResponse(status=ToolStatus.ERROR, message=str(e))


class A10Tool(BaseTool):
    agent_name = "A10"
    description = "Identify high-value (gold) ticket sales from a database and save them to a text file."
    parameters = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Input SQLite database file containing ticket sales",
                "default": "/data/ticket-sales.db",
            },
            "output_filename": {
                "type": "string",
                "description": "Output text file to write gold ticket sales total",
                "default": "/data/ticket-sales-gold.txt",
            },
            "query": {
                "type": "string",
                "description": "SQL query to calculate total gold ticket sales",
            },
        },
        "required": ["filename", "output_filename", "query"],
    }

    def run(
        self,
        filename="/data/ticket-sales.db",
        output_filename="/data/ticket-sales-gold.txt",
        query="SELECT SUM(units * price) FROM tickets WHERE type = 'Gold'",
    ):
        try:
            conn = sqlite3.connect(safe_path(filename))
            cursor = conn.cursor()

            cursor.execute(query)
            total_sales = cursor.fetchone()[0] or 0

            safe_write(output_filename, str(total_sales))

            conn.close()
            return ToolResponse(status=ToolStatus.SUCCESS)
        except Exception as e:
            return ToolResponse(status=ToolStatus.ERROR, message=str(e))
