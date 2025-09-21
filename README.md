# Calibre MCP Server

An MCP (Model Context Protocol) server that provides tools to interact with a Calibre e-book library, allowing search and retrieval of book metadata through the MCP protocol.

### Tools
| Tool                          | Description                                   | Parameters           |
| ----------------------------- | --------------------------------------------- | -------------------- |
| `search_books_by_title`       | Search books by title pattern with wildcards  | `title_pattern: str` |
| `search_authors_by_name`      | Search authors by name pattern with wildcards | `name_pattern: str`  |
| `get_books_by_author`         | Get all books by a specific author name       | `author_name: str`   |
| `get_books_by_author_id`      | Get all books by a specific author ID         | `author_id: int`     |
| `get_books_by_series`         | Get all books in a series, ordered by index   | `series_name: str`   |
| `get_books_by_tag`            | Get all books with a specific tag             | `tag_name: str`      |
| `search_books_by_tag_pattern` | Search books by tag pattern with wildcards    | `tag_pattern: str`   |
| `get_book_details`            | Get complete details for a specific book      | `book_id: int`       |
| `get_library_stats`           | Get comprehensive library statistics          | —                    |
| `get_all_tags`                | Get all available tags in the library         | —                    |

## Environment Variables
| Variable               | Default | Description                                                                 |
| ---------------------- | ------- | --------------------------------------------------------------------------- |
| `CALIBRE_LIBRARY_PATH` | —       | Required path to Calibre library (mandatory, if missing server won't start) |

## Features
- **Search capabilities**: Search books by title, author, series, and tags with wildcard support
- **Comprehensive metadata**: Retrieve complete book information including publication dates, series info, and tags
- **Library statistics**: Get insights into your Calibre library with comprehensive statistics
- **Tag management**: Browse and search through all available tags in your library
- **Author discovery**: Find authors and explore their complete bibliographies
- **Series tracking**: Access books in series with proper ordering by series index


## Usage

### Install as local package
Install the package:

```bash
python -m pip install .
```

#### Configuration example for Claude Desktop/Cursor/VSCode
Add this configuration to your application's settings (mcp.json):
```json
"calibre mcp server": {
    "type": "stdio",
    "command": "python",
    "args": [
        "-m",
        "calibre_mcp_server"
    ],
    "env": {
        "CALIBRE_LIBRARY_PATH": "C:\\Users\\YourUser\\Calibre Library"
    }
}
```


## Technical Notes
- Connection to Calibre database is performed automatically when the server starts.
- If the `CALIBRE_LIBRARY_PATH` is missing or invalid, the server generates an error and does not start.
- All database queries use SQLite for efficient access to Calibre's metadata.
- Search functions support SQL LIKE wildcards (%) for flexible pattern matching.
- The server provides read-only access to the Calibre library for safety.