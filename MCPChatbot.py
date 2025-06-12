from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List
import asyncio
import nest_asyncio

nest_asyncio.apply()
load_dotenv()

class MCPChatbot:
    def __init__(self):
        # Initialize the session and client objects
        self.session: ClientSession = None
        self.anthropic = Anthropic()
        self.available_tools: List[dict] = []
    
    async def process_query(self, query):
        messages = [{'role':'user', 'content':query}]
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
                    # print(f"Content: {content}")
                    final_response = content.text
                    assistant_content.append(content)
                    if(len(response.content) == 1):
                        process_query= False
                elif content.type == 'tool_use':
                    print(f"Content: {content}")
                    assistant_content.append(content)
                    messages.append({'role':'assistant', 'content':assistant_content})
                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name
    
                    print(f"Tool ID: {tool_id}, Tool Name: {tool_name}, Tool Args: {tool_args}")
                    
                    try:
                        # tool invocation through the client session
                        result = await self.session.call_tool(tool_name, arguments=tool_args)
                        messages.append({"role": "user", 
                                          "content": [
                                              {
                                                  "type": "tool_result",
                                                  "tool_use_id": tool_id,
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
                    except Exception as e:
                        error_msg = f"Error executing tool: {str(e)}"
                        print(error_msg)
                        messages.append({"role": "user", 
                                          "content": [
                                              {
                                                  "type": "tool_result",
                                                  "tool_use_id": tool_id,
                                                  "content": error_msg
                                              }
                                          ]
                                        })
                        response = self.anthropic.messages.create(max_tokens = 2024,
                                          model = 'claude-3-7-sonnet-20250219', 
                                          tools = self.available_tools,
                                          messages = messages)
                        final_response = response.content[0].text
                        process_query = False
        return final_response

    async def chat_loop(self):
        print("\nWelcome to the MCP Chatbot!")
        print("Type 'exit' to quit the chat.")
        
        while True:
            try:
                query = input("\nYou: ").strip()
                
                if query.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                    
                response = await self.process_query(query)
                print(f"Bot: {response}")
                    
            except Exception as e:
                print(f"An error occurred: {str(e)}")

    async def connect_to_server_and_run(self):
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command= "uv",
            args=["run", "ResearchServer.py"],
            env=None,
        )

        try:
            # Connect to the MCP server using stdio_client
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    self.session = session

                    # Initialize the connection to the server
                    await self.session.initialize()
                    print("Connected to the MCP server successfully!")

                    # List available tools
                    response = await session.list_tools()

                    tools = response.tools
                    print(f"Connected to server with {len(tools)} tools: {', '.join(tool.name for tool in tools)}")

                    self.available_tools = [
                        {
                            'name': tool.name,
                            'description': tool.description,
                            'input_schema': tool.inputSchema
                        } for tool in tools
                    ]
                
                    # IMPORTANT: Run the chat loop within the session context
                    await self.chat_loop()
        except Exception as e:
            print(f"Error connecting to server: {str(e)}")

async def main():
    chatbot = MCPChatbot()
    await chatbot.connect_to_server_and_run()

if __name__ == "__main__":
    asyncio.run(main())