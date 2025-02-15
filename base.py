from abc import ABC, abstractmethod
from openai_function_calling import FunctionInferrer
from pydantic import BaseModel


class ToolStatus:
    SUCCESS = "success"
    ERROR = "error"


class ToolResponse(BaseModel):
    """Data model for respones from agents."""

    status: str = ToolStatus.SUCCESS
    message: str = ""
    data: dict = {}


class BaseTool(ABC):
    """Interface for all agents. All agents should inherit from this class."""

    def get_parameters(self):
        """Return the automatically inferred parameters for the function using the dcstring of the function."""
        function_inferrer = FunctionInferrer.infer_from_function_reference(self.run)
        function_json = function_inferrer.to_json_schema()
        parameters = function_json.get("parameters")
        if not parameters:
            raise Exception(
                "Failed to infere parameters, please define JSON instead of using this automated util."
            )
        return parameters

    def to_llm_format(self):
        """Convert the agent to LLM tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @property
    def name(self):
        return self.agent_name

    @property
    def agent_description(self):
        return self.description

    def safe_call(self, *args, **kwargs):
        try:
            return self.run(*args, **kwargs)

        except Exception as e:
            return ToolResponse(status=ToolStatus.ERROR, message=str(e))

    @abstractmethod
    def run(*args, **kwargs) -> ToolResponse:
        pass
