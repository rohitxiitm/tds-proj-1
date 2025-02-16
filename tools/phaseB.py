import json
import logging
from base import BaseTool, ToolResponse, ToolStatus
from llm import ask_llm
import constants
import subprocess

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are an intelligent automation agent tasked with generating valid and secure "
    "Python or Bash scripts based on user instructions. Follow these strict rules:\n\n"
    "1. Ensure the script adheres to DataWorks security constraints:\n"
    "   - Do NOT access or exfiltrate data outside the '/data' directory.\n"
    "   - Do NOT delete any data anywhere on the file system.\n\n"
    "2. The script should support the following tasks:\n"
    "   - Fetching data from an API and saving it.\n"
    "   - Cloning a Git repository and making a commit.\n"
    "   - Running SQL queries on SQLite or DuckDB databases.\n"
    "   - Extracting (scraping) data from a website.\n"
    "   - Compressing or resizing images.\n"
    "   - Transcribing audio from an MP3 file.\n"
    "   - Converting Markdown to HTML.\n"
    "   - Writing an API endpoint that filters a CSV file and returns JSON data.\n\n"
    "3. If the task is not explicitly listed above, generate the script in a secure "
    "and reliable manner, following automation best practices.\n\n"
    "4. Return the response strictly in JSON format with only these fields:\n"
    "   - 'application_type': Must be either 'bash' or 'python'.\n"
    "   - 'task_code': The script code (without any formatting).\n"
    "   - 'setup_code': Optional bash script to install required packages.\n"
    "   Note: For setup_code, this runs in a Python:3.12-slim Docker container.\n"
    "   Do not use sudo or other privileged commands. Use apt-get for packages.\n\n"
    "5. If an error occurs, provide an improved version based on previous errors.\n\n"
    "6. For Python scripts, always wrap the main logic in a try-except block:\n"
    "   import sys\n"
    "   try:\n"
    "       # Main script logic here\n"
    "   except Exception as e:\n"
    "       print(f'Error: {str(e)}', file=sys.stderr)\n"
    "       sys.exit(1)\n\n"
    "7. For Bash scripts, always include error handling at the start:\n"
    "   set -e  # Exit on any error\n"
    "   trap 'echo \"Error: $BASH_COMMAND failed\" >&2' ERR\n"
    "   Note: Always use lowercase 'touch' command, not 'Touch'\n\n"
    "Your response must be valid JSON without additional text or formatting."
)


class CodeRunnerTool(BaseTool):
    name = "code_runner"
    description = (
        "A fallback tool that handles tasks when no other specialized tool matches. "
        "Automatically generates and executes secure code to fulfill arbitrary "
        "automation requirements following best practices."
    )
    parameters = {
        "type": "object",
        "properties": {
            "user_instruction": {
                "type": "string",
                "description": "Natural language instruction describing user "
                "instructions and requirements exactly",
            },
        },
        "required": ["user_instruction"],
    }

    def run_subprocess(self, code: str, application_type: str) -> (bool, str):
        """
        Run the given code in a subprocess, using Python or Bash.
        The code is provided via STDIN, not stored in a file.

        Returns:
            (success, output_or_error)
            success = True if return code == 0, otherwise False
            output_or_error = stdout if success, stderr if failure
        """
        if application_type == "python":
            # Run Python script from STDIN
            result = subprocess.run(
                ["python"], input=code, capture_output=True, text=True
            )
        elif application_type == "bash":
            # Run Bash script from STDIN
            result = subprocess.run(
                ["bash"], input=code, capture_output=True, text=True
            )
        else:
            return False, f"Unknown application_type: {application_type}"

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr

    def run(self, user_instruction: str):
        """
        1. Calls LLM with user instruction to generate code in either bash or python.
        2. Extracts the code and application type, runs in a subprocess (in-memory).
        3. If it fails, includes the previous code, error, and user instruction
           and asks LLM to fix it. Repeats until success or max_iterations is reached.
        """
        max_iterations = constants.CODE_RUNNER_MAX_ITERATIONS
        iteration = 0
        context = ""

        while iteration < max_iterations:
            iteration += 1

            # Build a robust prompt for the LLM
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"User instruction: {user_instruction}\n"
                        f"Context: {context}\n\n"
                        "Generate code to solve the user instruction."
                    ),
                },
            ]

            # Call the LLM to get the JSON response
            response = ask_llm(messages)
            logger.info(f"LLM Response: {response}")
            llm_raw_response = response.choices[0].message.content

            # Remove any ```json and ``` markers if present
            llm_raw_response = (
                llm_raw_response.replace("```json", "").replace("```", "").strip()
            )

            # Attempt to parse the JSON
            try:
                parsed_response = json.loads(llm_raw_response)
            except json.JSONDecodeError:
                # If we cannot parse, add error to context and try again
                error_msg = (
                    f"Could not parse LLM response as valid JSON:\n{llm_raw_response}"
                )
                logger.error(f"Attempt {iteration} failed:\n{error_msg}")
                context += f"\nError: {error_msg}"
                continue

            application_type = parsed_response.get("application_type", "").strip()
            task_code = parsed_response.get("task_code", "")
            setup_code = parsed_response.get("setup_code", "")

            # Run setup code if provided
            if setup_code:
                setup_success, setup_output = self.run_subprocess(setup_code, "bash")
                if not setup_success:
                    logger.error(f"Setup failed with error:\n{setup_output}")
                    context += (
                        f"\nSetup script failed:\n{setup_code}\n"
                        f"Error:\n{setup_output}\n"
                        f"Please fix the setup script accordingly."
                    )
                    continue

            # Run the main code in a subprocess (in-memory)
            success, output_or_error = self.run_subprocess(task_code, application_type)

            if success:
                logger.info(f"Script succeeded on iteration {iteration}")
                return ToolResponse(
                    status=ToolStatus.SUCCESS,
                    data={"output": output_or_error, "iterations": iteration},
                )
            else:
                logger.error(
                    f"Script failed on iteration {iteration} with error:\n{output_or_error}"
                )
                # Update context for next iteration
                context += (
                    f"\nPrevious code:\n{task_code}\n"
                    f"Previous setup code:\n{setup_code}\n"
                    f"Error:\n{output_or_error}\n"
                    f"Please fix the code accordingly."
                )

        return ToolResponse(
            status=ToolStatus.ERROR,
            message=f"Max iterations ({max_iterations}) reached. Script execution failed.",
        )
