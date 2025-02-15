import json
import logging
import os
import shutil
import sqlite3
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

import constants
import numpy as np
import requests
from base import BaseTool, ToolResponse, ToolStatus
from dateutil.parser import parse
from dotenv import load_dotenv
from llm import ask_llm, get_embedding
from utils import png_to_base64, safe_path, safe_read, safe_write

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
                "description": "Email address that will be passed as an argument to the script. This email is used to generate consistent test data.",
                "default": constants.DEFAULT_EMAIL,
            },
            "script_url": {
                "type": "string",
                "description": "URL of the Python script to execute. If not provided, defaults to the data generation script.",
                "default": constants.DATAGEN_SCRIPT_URL,
            },
        },
        "required": ["script_url", "email"],
    }

    def run(self, script_url, email):
        logger.info(f"Runnig tool {self.name}")

        save_at = safe_path("/data")
        if os.path.exists(save_at):
            try:
                shutil.rmtree(save_at)
                os.makedirs(save_at)
            except PermissionError:
                logger.error(
                    f"Permission denied: Unable to remove existing directory at {save_at}. "
                )

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
                status=ToolStatus.SUCCESS,
                data={"count": weekday_count, "weekday": weekday},
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
            "sort_keys": {
                "type": "array",
                "description": "List of keys to sort by, in order of priority",
                "items": {"type": "string"},
                "default": ["last_name", "first_name"],
            },
        },
        "required": ["filename", "targetfile"],
    }

    def run(
        self,
        filename="/data/contacts.json",
        targetfile="/data/contacts-sorted.json",
        sort_keys=["last_name", "first_name"],
    ):
        try:
            contacts = json.loads(safe_read(filename))
            sorted_contacts = sorted(
                contacts, key=lambda x: tuple(x[key] for key in sort_keys)
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
            "extension": {
                "type": "string",
                "description": "File extension to filter by (without dot)",
                "default": "log",
            },
        },
        "required": ["log_dir_path", "output_file_path", "num_files"],
    }

    def run(
        self,
        log_dir_path="/data/logs",
        output_file_path="/data/logs-recent.txt",
        num_files=10,
        extension="log",
    ):
        try:
            log_dir = Path(safe_path(log_dir_path))
            output_file = Path(safe_path(output_file_path))

            # Strip any leading dots from extension
            extension = extension.lstrip(".")

            log_files = sorted(
                log_dir.glob(f"*.{extension}"), key=os.path.getmtime, reverse=True
            )[:num_files]

            with output_file.open("w") as f_out:
                for i, log_file in enumerate(log_files):
                    with log_file.open("r") as f_in:
                        first_line = f_in.readline().strip()
                        if i < len(log_files) - 1:
                            f_out.write(f"{first_line}\n")
                        else:
                            f_out.write(first_line)
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
    description = (
        "Extract the email address from a text file and save it to an output file."
    )
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
            email_content = safe_read(filename)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an email parser. Extract ONLY the sender's email "
                        "address from the email content. Return just the email "
                        "address with no additional text or formatting."
                    ),
                },
                {"role": "user", "content": email_content},
            ]

            response = ask_llm(messages)
            sender_email = response.choices[0].message.content.strip()

            safe_write(output_file, sender_email)
            return ToolResponse(status=ToolStatus.SUCCESS)
        except Exception as e:
            return ToolResponse(status=ToolStatus.ERROR, message=str(e))


class A8Tool(BaseTool):
    agent_name = "A8"
    description = "Extract credit card number from an credit card image image (image path is expected) and save it to a text file."
    parameters = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Output text file path to save extracted card number",
                "default": "/data/credit-card.txt",
            },
            "input_image_path": {
                "type": "string",
                "description": "Path to input PNG image with credit card details",
                "default": "/data/credit-card.png",
            },
        },
        "required": ["filename", "input_image_path"],
    }

    def run(
        self, filename="/data/credit_card.txt", input_image_path="/data/credit_card.png"
    ):
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a secure credit card number extractor. Extract "
                        "ONLY the credit card number from the image. Return just "
                        "the digits without any spaces. Validate that it follows "
                        "standard credit card number format and length. Do not "
                        "extract or return any other sensitive data."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract the credit card number safely",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,"
                                f"{png_to_base64(safe_path(input_image_path))}"
                            },
                        },
                    ],
                },
            ]

            response = ask_llm(messages)
            card_number = response.choices[0].message.content.strip().replace(" ", "")

            # Validate card number format
            if not card_number.isdigit() or len(card_number) < 8:
                raise ValueError("Invalid credit card number format")

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
            # Read comments from file
            comments = safe_read(filename).splitlines()

            # Get embeddings using OpenAI API
            response = get_embedding(comments)
            embeddings = [emb.embedding for emb in response.data]

            # Calculate similarity matrix using dot product
            similarity = np.dot(embeddings, np.transpose(embeddings))

            # Mask diagonal to ignore self-similarity
            np.fill_diagonal(similarity, -np.inf)

            # Find indices of most similar pair
            i, j = np.unravel_index(similarity.argmax(), similarity.shape)

            # Write the similar comments to output file
            similar_comments = sorted([comments[i], comments[j]])
            safe_write(output_filename, "\n".join(similar_comments))

            return ToolResponse(status=ToolStatus.SUCCESS)
        except Exception as e:
            return ToolResponse(status=ToolStatus.ERROR, message=str(e))


class A10Tool(BaseTool):
    agent_name = "A10"
    description = (
        "Execute a SQL query on a SQLite database and save the results to a file. "
        "Useful for analyzing data stored in SQLite databases and extracting specific "
        "information based on custom queries."
    )
    parameters = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Path to the SQLite database file to query. Should be a "
                             "valid .db file containing the tables to analyze.",
                "default": "/data/ticket-sales.db",
            },
            "output_filename": {
                "type": "string", 
                "description": "Path where the query results will be saved as a text "
                             "file. The output will contain the raw query results.",
                "default": "/data/ticket-sales-gold.txt",
            },
            "query": {
                "type": "string",
                "description": "SQL query to execute on the database. Must be valid SQL "
                             "that returns a single value or result set to save.",
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
