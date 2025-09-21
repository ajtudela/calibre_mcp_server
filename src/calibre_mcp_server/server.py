"""
Calibre MCP Server - A Model Context Protocol server for Calibre e-book.

This server provides tools to interact with a Calibre e-book library,
allowing search and retrieval of book metadata through the MCP protocol.
"""

import os
import logging
from typing import Dict, List, Any
from typing import Annotated

from .calibre_api import Book, CalibreDB
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from dotenv import load_dotenv, find_dotenv
from pydantic import Field


# Load environment variables: prefer a .env in the current working directory
# (so running the installed package from the project root works). If not
# found, fallback to the .env bundled next to the package file.
dot_env_path = find_dotenv(usecwd=True)
if dot_env_path:
    load_dotenv(dot_env_path)
else:
    # fallback: .env next to this file's parent directory
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        '.env'
    )
    load_dotenv(env_path)

#############################################
# Configuration
#############################################
CALIBRE_LIBRARY_PATH: str = os.getenv("CALIBRE_LIBRARY_PATH", "")

if not CALIBRE_LIBRARY_PATH:
    raise ValueError(
        "CALIBRE_LIBRARY_PATH is not set in the .env file. Add it to .env."
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

mcp = FastMCP(name="Calibre MCP Server")

# Initialize CalibreDB instance
try:
    calibre_db = CalibreDB(CALIBRE_LIBRARY_PATH)
    logger.info(f"Calibre database initialized at: {CALIBRE_LIBRARY_PATH}")
except Exception as e:
    logger.error(f"Failed to initialize Calibre database: {e}")
    raise


#############################################
# Tools - Search Functions
#############################################


@mcp.tool(
    name="search_books_by_title",
    description=(
        "Search for books in the Calibre library by title pattern "
        "(supports wildcards like %)"
    ),
    tags={"search", "books", "title"},
    annotations={
        "title": "Search Books by Title",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def search_books_by_title(
    title_pattern: Annotated[str, Field(
        description=(
            "Title pattern to search for (use % for wildcards, "
            "e.g., 'Python%' or '%Django%')"
        ),
        min_length=1,
        max_length=200
    )]
) -> List[Dict[str, Any]]:
    """Search for books by title using pattern matching.

    Parameters
    ----------
    title_pattern : str
        Pattern to search in book titles. Supports SQL LIKE wildcards (%).

    Returns
    -------
    List[Dict[str, Any]]
        List of matching books with ID and title.

    Raises
    ------
    ToolError
        If search fails or no books are found.
    """
    try:
        results = calibre_db.search_books_by_title(title_pattern)
        if not results:
            raise ToolError(
                f"No books found with title pattern: '{title_pattern}'"
            )

        return [{"id": book_id, "title": title} for book_id, title in results]
    except ValueError as e:
        raise ToolError(str(e))
    except Exception as e:
        logger.error(f"Error searching books by title: {e}")
        raise ToolError(
            f"Database error occurred while searching for books: {str(e)}"
        )


@mcp.tool(
    name="search_authors_by_name",
    description=(
        "Search for authors in the Calibre library by name pattern "
        "(supports wildcards like %)"
    ),
    tags={"search", "authors", "name"},
    annotations={
        "title": "Search Authors by Name",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def search_authors_by_name(
    name_pattern: Annotated[str, Field(
        description=(
            "Author name pattern to search for (use % for wildcards, "
            "e.g., 'Stephen%' or '%King%')"
        ),
        min_length=1,
        max_length=200
    )]
) -> List[Dict[str, Any]]:
    """Search for authors by name using pattern matching.

    Parameters
    ----------
    name_pattern : str
        Pattern to search in author names. Supports SQL LIKE wildcards (%).

    Returns
    -------
    List[Dict[str, Any]]
        List of matching authors with ID and name.

    Raises
    ------
    ToolError
        If search fails or no authors are found.
    """
    try:
        results = calibre_db.search_authors_by_name(name_pattern)
        if not results:
            raise ToolError(
                f"No authors found with name pattern: '{name_pattern}'"
            )

        return [
            {"id": author_id, "name": name} for author_id, name in results
        ]
    except ValueError as e:
        raise ToolError(str(e))
    except Exception as e:
        logger.error(f"Error searching authors by name: {e}")
        raise ToolError(
            f"Database error occurred while searching for authors: {str(e)}"
        )


@mcp.tool(
    name="get_books_by_author",
    description="Get all books by a specific author name",
    tags={"search", "books", "author"},
    annotations={
        "title": "Get Books by Author",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def get_books_by_author(
    author_name: Annotated[str, Field(
        description="Exact name of the author to search for",
        min_length=1,
        max_length=200
    )]
) -> List[Dict[str, Any]]:
    """Get detailed information about all books by a specific author.

    Parameters
    ----------
    author_name : str
        Exact name of the author.

    Returns
    -------
    List[Dict[str, Any]]
        List of books with detailed information including series.

    Raises
    ------
    ToolError
        If author not found or database error occurs.
    """
    try:
        results = calibre_db.get_books_by_author(author_name)

        books = []
        for book_id, title, pub_date, series_info in results:
            books.append({
                "id": book_id,
                "title": title,
                "publication_date": pub_date,
                "series_info": series_info,
                "author": author_name
            })

        return books
    except ValueError as e:
        raise ToolError(str(e))
    except Exception as e:
        logger.error(f"Error getting books by author: {e}")
        raise ToolError(f"Database error occurred: {str(e)}")


@mcp.tool(
    name="get_books_by_author_id",
    description="Get all books by a specific author using their ID",
    tags={"search", "books", "author", "id"},
    annotations={
        "title": "Get Books by Author ID",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def get_books_by_author_id(
    author_id: Annotated[int, Field(
        description="Unique ID of the author in the Calibre database",
        gt=0
    )]
) -> List[Dict[str, Any]]:
    """Get detailed information about all books by a specific author ID.

    Parameters
    ----------
    author_id : int
        Unique ID of the author in the database.

    Returns
    -------
    List[Dict[str, Any]]
        List of books with detailed information including series.

    Raises
    ------
    ToolError
        If author not found or database error occurs.
    """
    try:
        results = calibre_db.get_books_by_author_id(author_id)

        books = []
        for book_id, title, pub_date, series_info in results:
            books.append({
                "id": book_id,
                "title": title,
                "publication_date": pub_date,
                "series_info": series_info,
                "author_id": author_id
            })

        return books
    except ValueError as e:
        raise ToolError(str(e))
    except Exception as e:
        logger.error(f"Error getting books by author ID: {e}")
        raise ToolError(f"Database error occurred: {str(e)}")


@mcp.tool(
    name="get_books_by_series",
    description="Get all books in a specific series, ordered by series index",
    tags={"search", "books", "series"},
    annotations={
        "title": "Get Books by Series",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def get_books_by_series(
    series_name: Annotated[str, Field(
        description="Exact name of the series to search for",
        min_length=1,
        max_length=200
    )]
) -> List[Dict[str, Any]]:
    """Get all books in a specific series ordered by series index.

    Parameters
    ----------
    series_name : str
        Exact name of the series.

    Returns
    -------
    List[Dict[str, Any]]
        List of books in series order with title and series index.

    Raises
    ------
    ToolError
        If series not found or database error occurs.
    """
    try:
        results = calibre_db.get_books_by_series(series_name)

        books = []
        for book_id, title, series_index in results:
            books.append({
                "id": book_id,
                "title": title,
                "series_index": series_index,
                "series_name": series_name
            })

        return books
    except ValueError as e:
        raise ToolError(str(e))
    except Exception as e:
        logger.error(f"Error getting books by series: {e}")
        raise ToolError(f"Database error occurred: {str(e)}")


@mcp.tool(
    name="get_books_by_tag",
    description="Get all books with a specific tag",
    tags={"search", "books", "tags"},
    annotations={
        "title": "Get Books by Tag",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def get_books_by_tag(
    tag_name: Annotated[str, Field(
        description="Exact name of the tag to search for",
        min_length=1,
        max_length=100
    )]
) -> List[Dict[str, Any]]:
    """Get detailed information about all books with a specific tag.

    Parameters
    ----------
    tag_name : str
        Exact name of the tag.

    Returns
    -------
    List[Dict[str, Any]]
        List of books with detailed information including authors.

    Raises
    ------
    ToolError
        If tag not found or database error occurs.
    """
    try:
        results = calibre_db.get_books_by_tag(tag_name)

        books = []
        for book_id, title, authors, pub_date in results:
            books.append({
                "id": book_id,
                "title": title,
                "authors": authors,
                "publication_date": pub_date,
                "tag": tag_name
            })

        return books
    except ValueError as e:
        raise ToolError(str(e))
    except Exception as e:
        logger.error(f"Error getting books by tag: {e}")
        raise ToolError(f"Database error occurred: {str(e)}")


@mcp.tool(
    name="search_books_by_tag_pattern",
    description=(
        "Search for books with tags matching a pattern "
        "(supports wildcards like %)"
    ),
    tags={"search", "books", "tags", "pattern"},
    annotations={
        "title": "Search Books by Tag Pattern",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def search_books_by_tag_pattern(
    tag_pattern: Annotated[str, Field(
        description=(
            "Tag pattern to search for (use % for wildcards, "
            "e.g., 'sci%' or '%fiction%')"
        ),
        min_length=1,
        max_length=100
    )]
) -> List[Dict[str, Any]]:
    """Search for books with tags matching a pattern.

    Parameters
    ----------
    tag_pattern : str
        Pattern to search in tag names. Supports SQL LIKE wildcards (%).

    Returns
    -------
    List[Dict[str, Any]]
        List of books with matching tag patterns.

    Raises
    ------
    ToolError
        If no books found or database error occurs.
    """
    try:
        results = calibre_db.search_books_by_tag(tag_pattern)

        books = []
        for book_id, title, authors, pub_date in results:
            books.append({
                "id": book_id,
                "title": title,
                "authors": authors,
                "publication_date": pub_date,
                "matching_tag_pattern": tag_pattern
            })

        return books
    except ValueError as e:
        raise ToolError(str(e))
    except Exception as e:
        logger.error(f"Error searching books by tag pattern: {e}")
        raise ToolError(f"Database error occurred: {str(e)}")


#############################################
# Tools - Book Information
#############################################


@mcp.tool(
    name="get_book_details",
    description="Get complete details for a specific book by ID",
    tags={"book", "details", "metadata"},
    annotations={
        "title": "Get Book Details",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def get_book_details(
    book_id: Annotated[int, Field(
        description="Unique ID of the book in the Calibre database",
        gt=0
    )]
) -> Dict[str, Any]:
    """Get complete metadata for a specific book.

    Parameters
    ----------
    book_id : int
        Unique ID of the book in the Calibre database.

    Returns
    -------
    Dict[str, Any]
        Complete book metadata including title, author, series, tags, etc.

    Raises
    ------
    ToolError
        If book not found or database error occurs.
    """
    try:
        book = Book(book_id, CALIBRE_LIBRARY_PATH)
        return book.to_json()
    except ValueError as e:
        raise ToolError(str(e))
    except FileNotFoundError as e:
        raise ToolError(f"Database file not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting book details: {e}")
        raise ToolError(f"Error retrieving book details: {str(e)}")


#############################################
# Tools - Library Statistics and Information
#############################################


@mcp.tool(
    name="get_library_stats",
    description="Get comprehensive statistics about the Calibre library",
    tags={"library", "statistics", "info"},
    annotations={
        "title": "Get Library Statistics",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def get_library_stats() -> Dict[str, Any]:
    """Get comprehensive statistics about the Calibre library.

    Returns
    -------
    Dict[str, Any]
        Dictionary containing library statistics and information.

    Raises
    ------
    ToolError
        If database error occurs.
    """
    try:
        return calibre_db.get_database_info()
    except Exception as e:
        logger.error(f"Error getting library stats: {e}")
        raise ToolError(f"Error retrieving library statistics: {str(e)}")


@mcp.tool(
    name="get_all_tags",
    description="Get all available tags in the Calibre library",
    tags={"tags", "library", "list"},
    annotations={
        "title": "Get All Tags",
        "readOnlyHint": True,
        "openWorldHint": False
    }
)
def get_all_tags() -> List[Dict[str, Any]]:
    """Get all available tags in the Calibre library.

    Returns
    -------
    List[Dict[str, Any]]
        List of all tags with ID and name, ordered alphabetically.

    Raises
    ------
    ToolError
        If database error occurs.
    """
    try:
        results = calibre_db.get_all_tags()
        return [{"id": tag_id, "name": tag_name}
                for tag_id, tag_name in results]
    except Exception as e:
        logger.error(f"Error getting all tags: {e}")
        raise ToolError(f"Error retrieving tags: {str(e)}")


def main() -> None:
    """Run the MCP server.

    Notes
    -----
    Default transport is stdio for local MCP integration. Uncomment the
    HTTP line for network serving inside a container environment.
    """
    # mcp.run(transport="http", host="0.0.0.0", port=9001)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
