import arxiv
import json
import os
from typing import List
from dotenv import load_dotenv
import anthropic

PAPER_DIR = "papers"

### Tool Functions

def search_papers(topic: str, max_results: int = 5) -> List [str]:
    """
    Search for academic papers on arXiv based on a given topic and store their info.
    Args:
        topic (str): The topic to search for.
        max_results (int): The maximum number of results to return.
    Returns:
        List[str]: A list of paper IDs in the search.
    """
    #use arxiv client to search for papers
    client = arxiv.Client()
    search = arxiv.Search(
        query=topic,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance
    )
    papers = client.results(search)

    # Create a dirrectory for this topic
    path=os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)

    file_path=os.path.join(path, "papers_info.json")

    # Load existing data if available
    try:
        with open(file_path, 'r') as f:
            papers_info = json.load(f)
    except FileNotFoundError:
        papers_info = {}
    
    # Store paper info
    paper_ids = []
    for paper in papers:
        paper_ids.append(paper.get_short_id())
        papers_info[paper.get_short_id()] = {
            "title": paper.title,
            "summary": paper.summary,
            "authors": [author.name for author in paper.authors],
            "published": paper.published.isoformat(),
            "updated": paper.updated.isoformat(),
            "pdf_url": paper.pdf_url
        }
    
    # Save the updated paper info to the file
    with open(file_path, 'w') as f:
        json.dump(papers_info, f, indent=2)
    
    print(f"Found {len(paper_ids)} papers on topic '{topic}'.")
    print(f"Paper info saved to {file_path}.")
    return paper_ids

# search_papers("machine learning", 3)


def extract_info(paper_id: str) -> str:
    """
    Search fo information about a specific paper across all topic directories.
    Args:
        paper_id (str): The ID of the paper to search for.
    Returns:
        JSON string with paper info if found, error message otherwise.
    """
    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, 'r') as f:
                        papers_info = json.load(f)
                        if paper_id in papers_info:
                            return json.dumps(papers_info[paper_id], indent=2)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading file {file_path}: {e}")
                    continue
    return f"No saved information found related to the paper {paper_id}"

# info = extract_info("1707.04849v1")
# print(info)

### Tool Schema

tools=[
    {
        "name": "search_papers",
        "description": "Search for academic papers on arXiv based on a given topic and store their information.",
        "input_schema":{
            "type": "object",
            "properties": {
                "topic":{
                    "type": "string",
                    "description": "The topic to search for."
                },
                "max_results": {
                    "type": "integer",
                    "description": "The maximum number of results to return.",
                    "default": 5
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name":"extract_info",
        "description": "Search for information about a specific paper across all topic directories.",
        "input_schema":{
            "type": "object",
            "properties":{
                "paper_id": {
                    "type": "string",
                    "description": "The ID of the paper to search for."
                }
            },
            "required": ["paper_id"]
        }
    }
]


### Tool Mapping
tool_mapping = {
    "search_papers": search_papers,
    "extract_info": extract_info
}

def execute_tool(tool_name: str, input_data: dict) -> str:
    """
    Execute a tool based on its name and input data.
    Args:
        tool_name (str): The name of the tool to execute.
        input_data (dict): The input data for the tool.
    Returns:
        str: The result of the tool execution.
    """
    result=tool_mapping[tool_name](**input_data)
    if result is None:
        result = json.dumps({"error": "The operation completed but didn't return any results."}, indent=2)
    elif isinstance(result, list):
        result = ','.join(result)
    elif isinstance(result, dict):
        result = json.dumps(result, indent=2)
    else:
        result = str(result)
    return result

load_dotenv()
client = anthropic.Client()

# def process_query(query: str) -> str:
#     """
#     Process a query using the Anthropic API.
#     Args:
#         query (str): The query to process.
#     Returns:
#         str: The response from the Anthropic API.
#     """
#     messages = [{'role': 'user', 'content': query}]
#     response = client.messages.create(
#         model="claude-3-7-sonnet-20250219",
#         tools=tools,
#         messages=messages,
#         max_tokens=1000,
#     )
    
#     process_query = True
#     final_response = ""
#     # Loop through the response content until all tool uses are processed
#     while process_query:
#         assistant_content=[]

#         for content in response.content:
#             if content.type == 'text':
#                 print(content.text)
#                 final_response = content.text
#                 # Adds the text content to the list of assistant contents
#                 assistant_content.append({"role": "assistant", "content": content.text})
#                 if len(response.content) == 1:
#                     process_query = False
#             elif content.type == 'tool_use':
#                 # Adds the tool request to the list of assistant contents
#                 # Records this in the conversation history as a message from the assistant
#                 assistant_content.append(content)
#                 messages.append({'role': 'assistant', 'content': assistant_content})

#                 # Executing the Tool
#                 tool_id= content.id
#                 tool_name=content.name
#                 tool_args=content.input
#                 print(f"Tool ID: {tool_id}, Tool Name: {tool_name}, Tool Args: {tool_args}")
#                 tool_result = execute_tool(tool_name, tool_args)

#                 # Sending Results Back to Claude
#                 messages.append({"role": "user", 
#                                   "content": [
#                                       {
#                                           "type": "tool_result",
#                                           "tool_use_id": tool_id,
#                                           "content": tool_result
#                                       }
#                                   ]
#                                 })
                
#                 # Create a new response with the updated messages
#                 response = client.messages.create(
#                     model="claude-3-7-sonnet-20250219",
#                     tools=tools,
#                     messages=messages,
#                     max_tokens=1000,
#                 )

#                 # Check if the response contains only text content
#                 if (len(response.content) == 1 and 
#                     response.content[0].type == 'text'):
#                     final_response = response.content[0].text
#                     process_query = False
#     return final_response

def process_query(query: str) -> str:
    """
    Process a query using the Anthropic API.
    Args:
        query (str): The query to process.
    Returns:
        str: The response from the Anthropic API.
    """
    messages = [{'role': 'user', 'content': query}]
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        tools=tools,
        messages=messages,
        max_tokens=1000,
    )
    
    process_query = True
    final_response = ""
    # Loop through the response content until all tool uses are processed
    while process_query:
        assistant_content = []

        for content in response.content:
            if content.type == 'text':
                print(content.text)
                final_response = content.text
                # Adds the text content to the list of assistant contents with proper type field
                assistant_content.append({"type": "text", "text": content.text})
                if len(response.content) == 1:
                    process_query = False
            elif content.type == 'tool_use':
                # Add the tool use with proper format including type field
                assistant_content.append({
                    "type": "tool_use",
                    "id": content.id,
                    "name": content.name,
                    "input": content.input
                })
                
                # Add the assistant message with properly formatted content
                messages.append({'role': 'assistant', 'content': assistant_content})

                # Executing the Tool
                tool_id = content.id
                tool_name = content.name
                tool_args = content.input
                print(f"Tool ID: {tool_id}, Tool Name: {tool_name}, Tool Args: {tool_args}")
                tool_result = execute_tool(tool_name, tool_args)

                # Sending Results Back to Claude
                messages.append({
                    "role": "user", 
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": tool_result
                        }
                    ]
                })
                
                # Create a new response with the updated messages
                response = client.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    tools=tools,
                    messages=messages,
                    max_tokens=1000,
                )

                # Check if the response contains only text content
                if (len(response.content) == 1 and 
                    response.content[0].type == 'text'):
                    final_response = response.content[0].text
                    process_query = False
    return final_response

def chat_loop():
    """
    Start a chat loop to process user queries.
    """
    print("Welcome to the Academic Paper Search Chatbot!")
    print("Type 'exit' to quit the chat.")
    
    while True:
        try:
            query = input("\nYou: ").strip()
            if query.lower() == 'exit':
                print("Exiting the chat. Goodbye!")
                break
            response = process_query(query)
            print(f"Bot: {response}")
        except Exception as e:
            print(f"An error occurred: {e}")

chat_loop()