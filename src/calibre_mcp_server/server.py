"""
Calibre MCP Server - A Model Context Protocol server for Calibre e-book.

This server provides tools to interact with a Calibre e-book library,
allowing search and retrieval of book metadata through the MCP protocol.
"""

import logging
from typing import Dict, List, Any, Optional, NoReturn
from typing import Annotated

from .calibre_api import Book, CalibreDB
from .config import config
from .exceptions import (
    DatabaseError,
    ValidationError,
    NotFoundError
)
from .validation import (
    validate_search_parameters,
    validate_positive_integer
)

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError
from pydantic import Field


# Configure logging
logger = logging.getLogger(__name__)

# Initialize FastMCP server with configuration
mcp = FastMCP(name=config.server_name)

# Initialize CalibreDB instance
try:
    calibre_db = CalibreDB(config.calibre_library_path)
    logger.info(
        f"Calibre database initialized at: {config.calibre_library_path}"
    )
except Exception as e:
    logger.error(f"Failed to initialize Calibre database: {e}")
    raise


class CalibreToolHandler:
    """Handler class for Calibre MCP tools with centralized error handling."""

    @staticmethod
    async def handle_error(
        operation: str,
        error: Exception,
        search_term: Optional[str] = None,
        ctx: Optional[Context] = None
    ) -> NoReturn:
        """
        Centralized error handling for all operations.

        Parameters
        ----------
        operation : str
            The operation being performed.
        error : Exception
            The exception that was raised.
        search_term : str, optional
            The search term used, by default None.
        ctx : Context, optional
            The MCP context for logging, by default None.

        Raises
        ------
        ToolError
            Formatted error for MCP client.
        """
        error_msg = str(error)

        # Log error to context if available
        if ctx:
            if search_term:
                await ctx.error(
                    f"Error in {operation} for '{search_term}': {error_msg}"
                )
            else:
                await ctx.error(f"Error in {operation}: {error_msg}")

        # Also log to standard logger for server-side debugging
        logger.error(f"Error in {operation}: {error}")

        if isinstance(error, (ValueError, ValidationError)):
            raise ToolError(str(error))
        elif isinstance(error, (DatabaseError, NotFoundError)):
            raise ToolError(str(error))
        else:
            if search_term:
                raise ToolError(
                    f"Database error occurred while {operation} "
                    f"for '{search_term}': {str(error)}"
                )
            else:
                raise ToolError(
                    f"Database error occurred during {operation}: "
                    f"{str(error)}"
                )

    @staticmethod
    def format_simple_results(
        results: List[tuple],
        id_key: str = "id",
        value_key: str = "name"
    ) -> List[Dict[str, Any]]:
        """
        Format simple id, value tuple results.

        Parameters
        ----------
        results : List[tuple]
            Raw database results with (id, value) structure.
        id_key : str, optional
            Key name for ID field, by default "id".
        value_key : str, optional
            Key name for value field, by default "name".

        Returns
        -------
        List[Dict[str, Any]]
            Formatted dictionaries.
        """
        return [{id_key: item[0], value_key: item[1]} for item in results]

    @staticmethod
    def format_book_search_results(
        results: List[tuple],
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Format book search results with appropriate context.

        Parameters
        ----------
        results : List[tuple]
            Raw database results.
        context : str, optional
            Additional context information, by default None.

        Returns
        -------
        List[Dict[str, Any]]
            Formatted book dictionaries.
        """
        books = []
        for result in results:
            book_dict = {
                "id": result[0],
                "title": result[1],
            }

            # Handle different result formats based on length
            if len(result) == 4:  # author or tag search results
                book_dict["authors"] = result[2] or ""
                book_dict["publication_date"] = result[3] or ""
                if context:
                    book_dict["context"] = context
            elif len(result) == 3:  # series search results
                book_dict["series_index"] = result[2] or 0.0
                if context:
                    book_dict["series_name"] = context

            books.append(book_dict)
        return books


#############################################
# Search Tools
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
async def search_books_by_title(
    title_pattern: Annotated[str, Field(
        description=(
            "Title pattern to search for (use % for wildcards, "
            "e.g., 'Python%' or '%Django%')"
        ),
        min_length=1,
        max_length=200
    )],
    ctx: Context
) -> List[Dict[str, Any]]:
    """
    Search for books by title using pattern matching.

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
        await ctx.info(f"Searching books by title pattern: '{title_pattern}'")

        validated_pattern = validate_search_parameters(title_pattern)
        results = calibre_db.search_books_by_title(validated_pattern)

        if not results:
            await ctx.warning(
                f"No books found matching pattern: '{validated_pattern}'"
            )
            raise NotFoundError(
                "books", validated_pattern, "title pattern"
            )

        await ctx.info(f"Found {len(results)} books matching title pattern")
        formatted_results = CalibreToolHandler.format_simple_results(
            results, "id", "title"
        )

        await ctx.debug(
            f"Returning {len(formatted_results)} formatted results"
        )
        return formatted_results

    except Exception as e:
        await CalibreToolHandler.handle_error(
            "searching books by title", e, title_pattern, ctx
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
async def search_authors_by_name(
    name_pattern: Annotated[str, Field(
        description=(
            "Author name pattern to search for (use % for wildcards, "
            "e.g., 'Stephen%' or '%King%')"
        ),
        min_length=1,
        max_length=200
    )],
    ctx: Context
) -> List[Dict[str, Any]]:
    """
    Search for authors by name using pattern matching.

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
        await ctx.info(f"Searching authors by name pattern: '{name_pattern}'")

        validated_pattern = validate_search_parameters(name_pattern)
        results = calibre_db.search_authors_by_name(validated_pattern)

        if not results:
            await ctx.warning(
                f"No authors found matching pattern: '{validated_pattern}'"
            )
            raise NotFoundError(
                "authors", validated_pattern, "name pattern"
            )

        await ctx.info(f"Found {len(results)} authors matching name pattern")
        formatted_results = CalibreToolHandler.format_simple_results(results)

        await ctx.debug(
            f"Returning {len(formatted_results)} formatted results"
        )
        return formatted_results

    except Exception as e:
        await CalibreToolHandler.handle_error(
            "searching authors by name", e, name_pattern, ctx
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
async def get_books_by_author(
    author_name: Annotated[str, Field(
        description="Exact name of the author to search for",
        min_length=1,
        max_length=200
    )],
    ctx: Context
) -> List[Dict[str, Any]]:
    """
    Get detailed information about all books by a specific author.

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
        await ctx.info(f"Getting books by author: '{author_name}'")

        validated_name = validate_search_parameters(author_name)
        results = calibre_db.get_books_by_author(validated_name)

        if not results:
            await ctx.warning(f"No books found for author: '{validated_name}'")

        await ctx.info(f"Found {len(results)} books by author")

        books = []
        for book_id, title, pub_date, series_info in results:
            books.append({
                "id": book_id,
                "title": title,
                "publication_date": pub_date or "",
                "series_info": series_info or "",
                "author": validated_name
            })

        await ctx.debug(f"Returning {len(books)} book records")
        return books

    except Exception as e:
        await CalibreToolHandler.handle_error(
            "getting books by author", e, author_name, ctx
        )


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
async def get_books_by_author_id(
    author_id: Annotated[int, Field(
        description="Unique ID of the author in the Calibre database",
        gt=0
    )],
    ctx: Context
) -> List[Dict[str, Any]]:
    """
    Get detailed information about all books by a specific author ID.

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
        await ctx.info(f"Getting books by author ID: {author_id}")

        validated_id = validate_positive_integer(author_id, "author_id")
        results = calibre_db.get_books_by_author_id(validated_id)

        await ctx.info(f"Found {len(results)} books by author ID")

        books = []
        for book_id, title, pub_date, series_info in results:
            books.append({
                "id": book_id,
                "title": title,
                "publication_date": pub_date or "",
                "series_info": series_info or "",
                "author_id": validated_id
            })

        await ctx.debug(f"Returning {len(books)} book records")
        return books

    except Exception as e:
        await CalibreToolHandler.handle_error(
            "getting books by author ID", e, str(author_id), ctx
        )


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
async def get_books_by_series(
    series_name: Annotated[str, Field(
        description="Exact name of the series to search for",
        min_length=1,
        max_length=200
    )],
    ctx: Context
) -> List[Dict[str, Any]]:
    """
    Get all books in a specific series ordered by series index.

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
        await ctx.info(f"Getting books in series: '{series_name}'")

        validated_name = validate_search_parameters(series_name)
        results = calibre_db.get_books_by_series(validated_name)

        await ctx.info(f"Found {len(results)} books in series")

        books = []
        for book_id, title, series_index in results:
            books.append({
                "id": book_id,
                "title": title,
                "series_index": series_index or 0.0,
                "series_name": validated_name
            })

        await ctx.debug(f"Returning {len(books)} series books")
        return books

    except Exception as e:
        await CalibreToolHandler.handle_error(
            "getting books by series", e, series_name, ctx
        )


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
async def get_books_by_tag(
    tag_name: Annotated[str, Field(
        description="Exact name of the tag to search for",
        min_length=1,
        max_length=100
    )],
    ctx: Context
) -> List[Dict[str, Any]]:
    """
    Get detailed information about all books with a specific tag.

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
        await ctx.info(f"Getting books with tag: '{tag_name}'")

        validated_name = validate_search_parameters(tag_name, 100)
        results = calibre_db.get_books_by_tag(validated_name)

        await ctx.info(f"Found {len(results)} books with tag")

        books = []
        for book_id, title, authors, pub_date in results:
            books.append({
                "id": book_id,
                "title": title,
                "authors": authors or "",
                "publication_date": pub_date or "",
                "tag": validated_name
            })

        await ctx.debug(f"Returning {len(books)} tagged books")
        return books

    except Exception as e:
        await CalibreToolHandler.handle_error(
            "getting books by tag", e, tag_name, ctx
        )


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
async def search_books_by_tag_pattern(
    tag_pattern: Annotated[str, Field(
        description=(
            "Tag pattern to search for (use % for wildcards, "
            "e.g., 'sci%' or '%fiction%')"
        ),
        min_length=1,
        max_length=100
    )],
    ctx: Context
) -> List[Dict[str, Any]]:
    """
    Search for books with tags matching a pattern.

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
        await ctx.info(f"Searching books by tag pattern: '{tag_pattern}'")

        validated_pattern = validate_search_parameters(tag_pattern, 100)
        results = calibre_db.search_books_by_tag(validated_pattern)

        await ctx.info(f"Found {len(results)} books matching tag pattern")

        books = []
        for book_id, title, authors, pub_date in results:
            books.append({
                "id": book_id,
                "title": title,
                "authors": authors or "",
                "publication_date": pub_date or "",
                "matching_tag_pattern": validated_pattern
            })

        await ctx.debug(f"Returning {len(books)} pattern-matched books")
        return books

    except Exception as e:
        await CalibreToolHandler.handle_error(
            "searching books by tag pattern", e, tag_pattern, ctx
        )


#############################################
# Book Information Tools
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
async def get_book_details(
    book_id: Annotated[int, Field(
        description="Unique ID of the book in the Calibre database",
        gt=0
    )],
    ctx: Context
) -> Dict[str, Any]:
    """
    Get complete metadata for a specific book.

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
        await ctx.info(f"Getting details for book ID: {book_id}")

        validated_id = validate_positive_integer(book_id, "book_id")
        book = Book(validated_id, config.calibre_library_path)
        book_details = book.to_json()

        book_title = book_details.get('title', 'Unknown')
        await ctx.debug(f"Retrieved details for book: '{book_title}'")
        return book_details

    except Exception as e:
        await CalibreToolHandler.handle_error(
            "getting book details", e, str(book_id), ctx
        )


#############################################
# Library Information Tools
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
async def get_library_stats(ctx: Context) -> Dict[str, Any]:
    """
    Get comprehensive statistics about the Calibre library.

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
        await ctx.info("Getting library statistics")

        stats = calibre_db.get_database_info()

        total_books = stats.get('total_books', 0)
        await ctx.debug(f"Library contains {total_books} books")
        return stats

    except Exception as e:
        await CalibreToolHandler.handle_error(
            "getting library statistics", e, None, ctx
        )


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
async def get_all_tags(ctx: Context) -> List[Dict[str, Any]]:
    """
    Get all available tags in the Calibre library.

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
        await ctx.info("Getting all available tags")

        results = calibre_db.get_all_tags()
        formatted_results = CalibreToolHandler.format_simple_results(results)

        await ctx.debug(f"Found {len(formatted_results)} tags")
        return formatted_results

    except Exception as e:
        await CalibreToolHandler.handle_error(
            "getting all tags", e, None, ctx
        )


def main() -> None:
    """
    Run the MCP server.

    The server uses the transport mode configured in the config module.
    Default is stdio for local MCP integration. HTTP mode can be used
    for network serving in container environments.
    """
    if config.transport_mode.lower() == "http":
        logger.info(
            f"Starting HTTP server on {config.http_host}:{config.http_port}"
        )
        mcp.run(
            transport="http",
            host=config.http_host,
            port=config.http_port
        )
    else:
        logger.info("Starting server with stdio transport")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
