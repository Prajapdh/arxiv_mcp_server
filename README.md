# Academic Paper Search with MCP

This project demonstrates the Model Context Protocol (MCP) architecture with a server that provides academic paper search capabilities and a client that connects to multiple MCP servers in a chatbot interface.

## Project Overview

This application consists of:

1. **MCP Server (`ResearchServer.py`)**: Provides tools, resources, and prompts for searching and exploring academic papers from arXiv.
2. **MCP Client (`MCPChatbotWithMultipleServers.py`)**: A chatbot interface that can connect to multiple MCP servers and use their tools, resources, and prompts.

## Features

### MCP Server
- 🔍 **Search Papers**: Search for academic papers on arXiv by topic
- 📋 **Extract Info**: Get detailed information about specific papers
- 📂 **Browse Resources**: View paper topics and contents through URI-based resources
- 📝 **Prompts**: Generate structured prompts for research tasks

### MCP Client
- 🤖 **Chatbot Interface**: Natural language interface to the MCP servers
- 🌐 **Multi-Server Support**: Connect to multiple MCP servers simultaneously
- 🧰 **Resource Navigation**: Browse paper topics with `@` commands
- ⚡ **Prompt Execution**: Run predefined prompts with `/` commands

## Prerequisites

- Python 3.9+
- Node.js (for the MCP Inspector)

## Installation

1. Clone this repository:
```powershell
git clone https://github.com/Prajapdh/arxiv_mcp_server.git
cd arxiv_mcp_server
```

2. Install dependencies:
```powershell
pip install -r requirements.txt
```

3. Create a `.env` file with your Anthropic API key:
```
ANTHROPIC_API_KEY=your_api_key_here
```

4. Configure your servers in `server_config.json`:
```json
{
  "mcpServers": {
    "research": {
      "command": "uv",
      "args": ["run", "ResearchServer.py"],
      "env": null
    }
  }
}
```

## Running the MCP Server

### Run with stdio transport (default)
```powershell
uv run ResearchServer.py
```

### Run with MCP Inspector for debugging
```powershell
npx @modelcontextprotocol/inspector uv run ResearchServer.py
```

## Running the MCP Client

```powershell
uv run MCPChatbotWithMultipleServers.py
```

## Chatbot Commands

- **Regular query**: Type any text to chat with the assistant
- **`@folders`**: List all available paper topic folders
- **`@<topic>`**: Browse papers in a specific topic
- **`/prompts`**: List all available prompts
- **`/prompt <name> <arg1=value1>`**: Execute a specific prompt with arguments
- **`exit`**: Exit the chatbot

## Server Features

### Tools
| Tool | Description |
|------|-------------|
| `search_papers` | Search for papers on arXiv based on a topic |
| `extract_info` | Get detailed information about a specific paper |

### Resources
| Resource | Description |
|----------|-------------|
| `papers://folders` | List all available topic folders |
| `papers://{topic}` | Get detailed information about papers in a specific topic |

### Prompts
| Prompt | Description |
|--------|-------------|
| `generate_search_prompt` | Generate a prompt for Claude to find and discuss academic papers |

## Project Structure

```
DeepLearning MCP tutorial/
├── MCPChatbotWithMultipleServers.py  # Multi-server MCP client
├── ResearchServer.py                 # ArXiv paper search MCP server
├── server_config.json                # Server connection configuration
├── requirements.txt                  # Project dependencies
├── papers/                           # Directory for storing paper information
│   └── {topic}/                      # Topic-specific directories
│       └── papers_info.json          # Stored paper metadata
└── README.md                         # This file
```

## Understanding MCP

The Model Context Protocol (MCP) is a standard for connecting large language models (LLMs) to external tools and resources. In this project:

- The MCP server exposes tools (functions), resources (data sources), and prompts (templates)
- The MCP client connects to these servers and enables the LLM to use their capabilities
- Communication happens via either stdio (for local use) or SSE (for network use)

## Extending the Project

- Add more MCP servers with different capabilities
- Implement additional paper analysis tools
- Add support for other academic databases
- Create visualization tools for research data

## Troubleshooting

- If you encounter connection errors, ensure the server is running before starting the client
- For SSE transport issues, check port availability or switch to stdio transport
- Verify your Anthropic API key is correctly set in the .env file

## License

[MIT License](LICENSE)