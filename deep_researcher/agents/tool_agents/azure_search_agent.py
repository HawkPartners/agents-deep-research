"""
Agent used to perform searches against Azure AI Search and summarize the results.

The AzureSearchAgent provides two main capabilities:
1. PowerPoint Report Discovery: Find relevant PowerPoint reports based on a query (always use this first to find relevant file names)
2. Specific PowerPoint Report Retrieval: Get the content of a specific PowerPoint report (only use this after you have a file name from discovery)

The agent takes as input a string in the format of AgentTask.model_dump_json(), or can take a simple query string as input
"""

from ...llm_config import LLMConfig, model_supports_structured_output
from . import ToolAgentOutput
from ..baseclass import ResearchAgent
from ..utils.parse_output import create_type_parser
from ...tools.azure_search import create_azure_search_tools

INSTRUCTIONS = f"""You are a research assistant that specializes in retrieving and summarizing information from the internal Hawk Partners knowledge base of PowerPoint reports.

You have two main capabilities:
1. PowerPoint Report Discovery: Use the discover_powerpoint_reports tool to find the most relevant PowerPoint reports based on a query. This tool should always be used first to identify which reports exist and are relevant (it searches by file name and metadata).
2. Specific PowerPoint Report Retrieval: Use the retrieve_powerpoint_report tool to get the content of a specific PowerPoint report. Only use this tool after you have identified a relevant file name from the discovery step. This tool retrieves the actual content (slides and text) from the report.

When using these capabilities:
- Always start with discover_powerpoint_reports to find relevant file names
- Only use retrieve_powerpoint_report after you have a file name to get the content
- Always include citations/sources in your summaries
- Use headings and bullets to organize information when appropriate

Only output JSON. Follow the JSON schema below. Do not output anything else. I will be parsing this with Pydantic so output valid JSON only:
{ToolAgentOutput.model_json_schema()}
"""

def init_azure_search_agent(config: LLMConfig) -> ResearchAgent:
    """Initialize the Azure AI Search agent for PowerPoint reports only."""
    selected_model = config.fast_model
    search_tools = create_azure_search_tools()

    return ResearchAgent(
        name="AzureSearchAgent",
        instructions=INSTRUCTIONS,
        tools=search_tools,
        model=selected_model,
        output_type=ToolAgentOutput if model_supports_structured_output(selected_model) else None,
        output_parser=create_type_parser(ToolAgentOutput) if not model_supports_structured_output(selected_model) else None
    ) 