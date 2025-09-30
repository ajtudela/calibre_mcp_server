# Calibre MCP Server
![License](https://img.shields.io/github/license/ajtudela/calibre_mcp_server)

An MCP (Model Context Protocol) server that provides tools to interact with a Calibre e-book library, allowing search and retrieval of book metadata through the MCP protocol.

### Tools
| Tool                            | Description                                   | Parameters           |
| ------------------------------- | --------------------------------------------- | -------------------- |
| **search_books_by_title**       | Search books by title pattern with wildcards  | `title_pattern: str` |
| **search_authors_by_name**      | Search authors by name pattern with wildcards | `name_pattern: str`  |
| **get_books_by_author**         | Get all books by a specific author name       | `author_name: str`   |
| **get_books_by_author_id**      | Get all books by a specific author ID         | `author_id: int`     |
| **get_books_by_series**         | Get all books in a series, ordered by index   | `series_name: str`   |
| **get_books_by_tag**            | Get all books with a specific tag             | `tag_name: str`      |
| **search_books_by_tag_pattern** | Search books by tag pattern with wildcards    | `tag_pattern: str`   |
| **get_book_details**            | Get complete details for a specific book      | `book_id: int`       |
| **get_library_stats**           | Get comprehensive library statistics          | —                    |
| **get_all_tags**                | Get all available tags in the library         | —                    |

## Configuration

The server supports flexible configuration through environment variables:

| Variable               | Default              | Description                                 |
| ---------------------- | -------------------- | ------------------------------------------- |
| `CALIBRE_LIBRARY_PATH` | —                    | **Required** path to Calibre library        |
| `CALIBRE_DB_FILENAME`  | `metadata.db`        | Database filename within library            |
| `LOG_LEVEL`            | `INFO`               | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT`           | Default format       | Custom logging format string                |
| `MCP_SERVER_NAME`      | `Calibre MCP Server` | Server name for MCP protocol                |
| `TRANSPORT_MODE`       | `stdio`              | Transport mode (`stdio` or `http`)          |
| `HTTP_HOST`            | `0.0.0.0`            | HTTP host when using HTTP transport         |
| `HTTP_PORT`            | `9001`               | HTTP port when using HTTP transport         |

### Environment Setup
1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your settings:
```bash
# Required
CALIBRE_LIBRARY_PATH=/path/to/your/calibre/library

# Optional
LOG_LEVEL=DEBUG
TRANSPORT_MODE=http
```

## Features
- **Advanced search capabilities**: Search books by title, author, series, and tags with wildcard support
- **Comprehensive metadata**: Retrieve complete book information including publication dates, series info, and tags
- **Library statistics**: Get insights into your Calibre library with comprehensive statistics
- **Tag management**: Browse and search through all available tags in your library
- **Author discovery**: Find authors and explore their complete bibliographies
- **Series tracking**: Access books in series with proper ordering by series index

## Installation

### Install with uv (recommended)

Clone the repository and install with uv:

```bash
git clone https://github.com/ajtudela/calibre_mcp_server.git
cd calibre_mcp_server
cp .env.example .env
# Edit .env file with your Calibre library path
uv sync
```

Or install directly from the repository:

```bash
uv add git+https://github.com/ajtudela/calibre_mcp_server.git
```

### Install with pip

Install the package in mode:

```bash
git clone https://github.com/ajtudela/calibre_mcp_server.git
cd calibre_mcp_server
cp .env.example .env
# Edit .env file with your Calibre library path
python3 -m pip install .
```

Or install directly from the repository:

```bash
python3 -m pip install git+https://github.com/ajtudela/calibre_mcp_server.git
```

## Usage

### Running with uv

```bash
uv run calibre_mcp_server
```

### Running with pip installation

```bash
python3 -m calibre_mcp_server
```

### HTTP Mode (for containers)

To run in HTTP mode for containerized environments:

```bash
# Set environment variable
export TRANSPORT_MODE=http
export HTTP_HOST=0.0.0.0
export HTTP_PORT=9001
```

### Configuration example for Claude Desktop/Cursor/VSCode

#### Using uv (recommended)

Add this configuration to your application's settings (mcp.json):

```json
{
  "calibre mcp server": {
    "type": "stdio",
    "command": "uv",
    "args": [
      "run",
      "--directory",
      "/path/to/calibre_mcp_server",
      "calibre_mcp_server"
    ],
    "env": {
        "CALIBRE_LIBRARY_PATH": "YOUR_CALIBRE_LIBRARY_PATH"
    }
  }
}
```

#### Using pip installation

```json
{
  "calibre mcp server": {
    "type": "stdio",
    "command": "python3",
    "args": [
      "-m",
      "calibre_mcp_server"
    ],
    "env": {
        "CALIBRE_LIBRARY_PATH": "YOUR_CALIBRE_LIBRARY_PATH"
    }
  }
}
```

## Technical Notes
- **Database connection**: Automatic connection management with proper error handling
- **Configuration validation**: Startup validation ensures all required settings are present
- **SQLite optimization**: Efficient queries with proper indexing and connection pooling
- **Search patterns**: Support for SQL LIKE wildcards (%) for flexible pattern matching
- **Read-only access**: Safe, read-only access to Calibre library database
- **Memory efficient**: Optimized queries and proper resource cleanup
- **Error recovery**: Graceful handling of database errors and network issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the established patterns
4. Ensure all modules compile without errors
5. Update documentation as needed
6. Submit a pull request

## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.