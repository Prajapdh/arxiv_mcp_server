from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from contextlib import AsyncExitStack
from mcp.client.stdio import stdio_client
from typing import List, TypedDict, Dict
import asyncio
import nest_asyncio
import json

nest_asyncio.apply()
load_dotenv()

class ToolDefination(TypedDict):
    name: str
    description: str
    input_schema: dict

class PromptDefinition(TypedDict):
    name: str
    description: str
    arguments: dict

class MCPChatbot:
    def __init__(self):
        # Initialize the session and client objects
        self.sessions: List[ClientSession] = []
        # exit_stack is a context manager that will manage the mcp client objects and their sessions and ensures that they are properly closed.
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.available_tools: List[ToolDefination] = []
        self.available_prompts: List[PromptDefinition] = []
        # tool_to_session maps the tool name to the corresponding client session; in this way, when the LLM decides on a particular tool name, you can map it to the correct client session so you can use that session to send tool_call request to the right MCP server.
        self.tool_to_session: Dict[str, ClientSession] = {}
        self.prompt_to_session: Dict[str, ClientSession] = {}
        self.resource_to_session: Dict[str, ClientSession] = {}

    
    async def connect_to_server(self, server_name: str, server_config: dict)-> None:
        """
        Connect to a server and create a session.
        Args:
            server_name: Name of the server to connect to.
            server_config: Configuration for the server connection.
        """
        try:
            server_params = StdioServerParameters(**server_config)
            # Create a stdio transport for the server
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            # Create a new ClientSession for the server
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )

            await session.initialize()
            self.sessions.append(session)
            print(f"\nConnected to server: {server_name}")

            try:
                # List the tools available on the server
                response = await session.list_tools()
                tools = response.tools
                print(f"Tools available on {server_name}: {[t.name for t in tools]}\n")

                for tool in tools:
                    self.tool_to_session[tool.name] = session
                    self.available_tools.append({
                        'name': tool.name,
                        'description': tool.description,
                        'input_schema': tool.inputSchema
                    })

                # List available prompts
                prompts_response = await session.list_prompts()
                print(f"Prompts available on {server_name}: {[p.name for p in prompts_response.prompts]}\n")

                if prompts_response and prompts_response.prompts:
                    for prompt in prompts_response.prompts:
                        self.prompt_to_session[prompt.name] = session
                        self.available_prompts.append({
                            "name": prompt.name,
                            "description": prompt.description,
                            "arguments": prompt.arguments
                        })

                # List available resources
                resources_response = await session.list_resources()
                print(f"Resources available on {server_name}: {[str(r.uri) for r in resources_response.resources]}\n")
                if resources_response and resources_response.resources:
                    for resource in resources_response.resources:
                        resource_uri = str(resource.uri)
                        self.resource_to_session[resource_uri] = session
            except Exception as e:
                print(f"❌ Error listing tools or prompts or resources on server {server_name}: {str(e)}")
                raise
        except Exception as e:
            print(f"❌ Failed to connect to server {server_name}: {str(e)}")
    
    async def connect_to_servers(self):
        """
        Connect to multiple servers based on the configuration.
        """
        try:
            with open("./server_config.json", "r") as f:
                data = json.load(f)
            
            servers = data.get("mcpServers", {})

            for server_name, server_config in servers.items():
                await self.connect_to_server(server_name, server_config)
        except Exception as e:
            print(f"❌ Error loading server configuration: {str(e)}")
            raise
    

    async def process_query(self, query: str) -> str:
        """
        Process the user's query and return a response.
        Args:
            query: The user's input query.
        Returns:
            The response from the LLM or tool.
        """
        messages = [{'role':'user', 'content': query}]
        response = self.anthropic.messages.create(max_tokens = 2024,
                                      model = 'claude-3-7-sonnet-20250219', 
                                      tools = self.available_tools, # tools exposed to the LLM
                                      messages = messages)
        process_query = True
        final_response = ""
        while process_query:
            assistant_content = []
            for content in response.content:
                if content.type =='text':
                    # print(content.text)
                    final_response = content.text
                    assistant_content.append(content)
                    if(len(response.content) == 1):
                        process_query= False
                elif content.type == 'tool_use':
                    assistant_content.append(content)
                    messages.append({'role':'assistant', 'content':assistant_content})
                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name
                    
    
                    print(f"Calling tool {tool_name} with args {tool_args}")
                    
                    # Call a tool
                    session = self.tool_to_session[tool_name] # new
                    result = await session.call_tool(tool_name, arguments=tool_args)
                    messages.append({"role": "user", 
                                      "content": [
                                          {
                                              "type": "tool_result",
                                              "tool_use_id":tool_id,
                                              "content": result.content
                                          }
                                      ]
                                    })
                    response = self.anthropic.messages.create(max_tokens = 2024,
                                      model = 'claude-3-7-sonnet-20250219', 
                                      tools = self.available_tools,
                                      messages = messages)
                    if(len(response.content) == 1 and response.content[0].type == "text"):
                        print(response.content[0].text)
                        process_query= False
                        final_response = response.content[0].text
        
        return final_response

    async def get_resource(self, resource_uri: str) -> str:
        """
        Retrieve a resource from the MCP server.
        Args:
            resource_uri: The URI of the resource to retrieve.
        Returns:
            The content of the resource.
        """
        session = self.resource_to_session[resource_uri]
            
        # Fallback for paper URIs
        if not session and resource_uri.startswith("papers://"):
            for uri, sess in self.resource_to_session.items():
                if uri.startswith("papers://"):
                    session = sess
                    break
        if not session:
            return f"❌ No session found for resource {resource_uri}. Please check the resource URI or server connection."

        try:
            result = await session.read_resource(uri=resource_uri)
            # print(f"\n📄 Resource URI: {resource_uri}")
            # print(f"Resource contents: {result.contents}")
            if result and result.contents:
                output=f"\nRetrieved resource: {resource_uri}"
                output+="Content:"
                output+=result.contents[0].text
                return output
            else:
                return f"Resource {resource_uri} is empty, no content available."
        except KeyError:
            return f"❌ Resource {resource_uri} not found."
        except Exception as e:
            return f"❌ Error retrieving resource: {str(e)}"

    async def list_prompts(self):
        """
        List all available prompts from the MCP servers.
        Returns:
            A list of prompt names and descriptions.
        """
        if not self.available_prompts:
            return "No prompts available."

        output = "Available Prompts:\n"
        for prompt in self.available_prompts:
            output += f"- {prompt['name']}: {prompt['description']}\n"
            if prompt['arguments']:
                output += "  Arguments:\n"
                for arg in prompt['arguments']:
                    arg_name = arg.name if hasattr(arg, 'name') else arg.get('name', '')
                    output += f"    - {arg_name}\n"
        
        return output
    
    async def execute_prompt(self, prompt_name: str, arguments: dict) -> str:
        """
        Execute a prompt with the given name and arguments.
        Args:
            prompt_name: The name of the prompt to execute.
            arguments: The arguments to pass to the prompt.
        """
        session = self.prompt_to_session.get(prompt_name)
        if not session:
            return f"❌ Prompt '{prompt_name}' not found."

        try:
            result = await session.get_prompt(prompt_name, arguments=arguments)
            if result and result.messages:
                prompt_content = result.messages[0].content

                # Extract text from content (handles different formats)
                if isinstance(prompt_content, str):
                    text = prompt_content
                elif hasattr(prompt_content, 'text'):
                    text = prompt_content.text
                else:
                    text = " ".join(item.text if hasattr(item, 'text') else str(item) 
                                    for item in prompt_content)
                
                print(f"\n📃 Executing prompt '{prompt_name}' with arguments {arguments}:\n{text}")
                return await self.process_query(text)
        except Exception as e:
            return f"❌ Error executing prompt '{prompt_name}': {str(e)}"

    async def chat_loop(self):
        """
        Main chat loop to interact with the user.
        """
        print("\nWelcome to the MCP Chatbot! Type 'exit' to quit.")
        print("Use @folders to see available topics")
        print("Use @<topic> to search papers in that topic")
        print("Use /prompts to list available prompts")
        print("Use /prompt <name> <arg1=value1> to execute a prompt")

        while True:
            try:
                query = input("🧑 You: ").strip()
                if not query:
                    print("❌ Please enter a valid query.")
                    continue

                if query.lower() == 'exit':
                    break

                # Check for @resource syntax
                if query.startswith('@'):
                    # Remove the '@' and get the topic
                    topic = query[1:].strip()
                    if topic == "folders":
                        resource_uri = "papers://folders"
                    else:
                        resource_uri = f"papers://{topic}"
                    resource = await self.get_resource(resource_uri)
                    print(f"\n📄 Resource: {resource}")
                    continue

                # Check for / commands
                if query.startswith('/'):
                    parts = query.split()
                    command = parts[0].lower()

                    if command == '/prompts':
                        prompts_list = await self.list_prompts()
                        print(prompts_list)
                    elif command == '/prompt':
                        if len(parts) < 2:
                            print("Usage: /prompt <name> <arg1=value1> <arg1=value1> ...")
                        prompt_name = parts[1]
                        arguments = {}
                        for arg in parts[2:]:
                            if '=' in arg:
                                key, value = arg.split('=', 1)
                                arguments[key.strip()] = value.strip()
                        
                        prompt_response = await self.execute_prompt(prompt_name, arguments)
                        print(f"\n📜 Prompt Response: {prompt_response}")
                    else:
                        print(f"❌ Unknown command: {command}")
                    continue
                
                # Process the query normally
                response = await self.process_query(query)
                print(f"🤖 Bot: {response}")
            except Exception as e:
                print(f"❌ Error processing query: {str(e)}")
                continue
    
    async def cleanup(self):
        """
        Cleanup resources and close sessions.
        """
        await self.exit_stack.aclose()
        print("Closed all sessions and cleaned up resources.")
    

async def main():
    chatbot = MCPChatbot()

    try:
        # the mcp clients and sessions are not initialized using "with"
        # like in the previous lesson
        # so the cleanup should be manually handled
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    finally:
        await chatbot.cleanup()

if __name__ == "__main__":
    asyncio.run(main())