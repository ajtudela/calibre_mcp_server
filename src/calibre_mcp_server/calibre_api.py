"""
Calibre API module for database interactions.

This module provides classes and functions for interacting with Calibre's
SQLite database, including book metadata retrieval and search operations.
"""

import os
import sqlite3
import logging
from typing import List, Tuple, Generator, Dict, Any, Optional
from contextlib import contextmanager
from pathlib import Path

from .exceptions import (
    DatabaseError,
    NotFoundError,
    ConfigurationError
)
from .validation import validate_positive_integer, validate_search_parameters


logger = logging.getLogger(__name__)


@contextmanager
def database_connection(
    db_path: str
) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for SQLite database connections with error handling.

    Parameters
    ----------
    db_path : str
        Path to the SQLite database file.

    Yields
    ------
    sqlite3.Connection
        Database connection object.

    Raises
    ------
    DatabaseError
        If there is a database connection error.
    """
    if not Path(db_path).exists():
        raise DatabaseError(
            f'Database file not found: {db_path}',
            'connection'
        )

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise DatabaseError(
            f'Database connection failed: {e}',
            'connection'
        )
    finally:
        if conn:
            conn.close()


class Book:
    """
    Represents a book with its metadata from the Calibre database.

    This class loads and manages all metadata for a single book,
    providing a clean interface for accessing book information.
    """

    def __init__(
        self,
        book_id: int,
        library_path: str,
        db_filename: str = 'metadata.db'
    ) -> None:
        """
        Initialize a Book instance with metadata from Calibre database.

        Parameters
        ----------
        book_id : int
            Book ID (must be positive).
        library_path : str
            Path to the Calibre library folder.
        db_filename : str, optional
            Name of the SQLite database file, by default 'metadata.db'.

        Raises
        ------
        ValidationError
            If book_id is not a positive integer.
        ConfigurationError
            If library_path is invalid.
        DatabaseError
            If database file is not found or there's a connection error.
        NotFoundError
            If the book ID is not found in the database.
        """
        # Validate inputs
        self.id = validate_positive_integer(book_id, 'book_id')

        if not library_path or not isinstance(library_path, str):
            raise ConfigurationError(
                'Library path must be a non-empty string',
                'library_path'
            )

        # Initialize attributes with default values
        self.title = ''
        self.title_sort = ''
        self.date = ''
        self.author = ''
        self.author_sort = ''
        self.series = ''
        self.series_sort = ''
        self.series_idx = 0.0
        self.publisher = ''
        self.identifiers = ''
        self.language = ''
        self.synopsis = ''
        self.tags = ''

        # Set up database path
        self.db_path = os.path.join(library_path, db_filename)

        # Load book data
        self._load_book_data()

    def _load_book_data(self) -> None:
        """
        Load all book data from the database in a single optimized query.

        This method performs a comprehensive join to retrieve all book
        metadata in one database operation for better performance.

        Raises
        ------
        DatabaseError
            If there's a database error during data loading.
        NotFoundError
            If the book ID is not found in the database.
        """
        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()

                # Comprehensive query to get all book data at once
                query = """
                    SELECT
                        b.title,
                        b.sort,
                        b.pubdate,
                        b.series_index,
                        GROUP_CONCAT(DISTINCT a.name ORDER BY a.name)
                        as authors,
                        GROUP_CONCAT(DISTINCT a.sort ORDER BY a.sort)
                        as author_sorts,
                        s.name as series_name,
                        s.sort as series_sort,
                        GROUP_CONCAT(DISTINCT p.name ORDER BY p.name)
                        as publishers,
                        GROUP_CONCAT(DISTINCT i.type || ':' || i.val
                                     ORDER BY i.type) as identifiers,
                        l.lang_code as language,
                        c.text as synopsis,
                        GROUP_CONCAT(DISTINCT t.name ORDER BY t.name) as tags
                    FROM books b
                    LEFT JOIN books_authors_link bal ON b.id = bal.book
                    LEFT JOIN authors a ON bal.author = a.id
                    LEFT JOIN books_series_link bsl ON b.id = bsl.book
                    LEFT JOIN series s ON bsl.series = s.id
                    LEFT JOIN books_publishers_link bpl ON b.id = bpl.book
                    LEFT JOIN publishers p ON bpl.publisher = p.id
                    LEFT JOIN identifiers i ON b.id = i.book
                    LEFT JOIN books_languages_link bll ON b.id = bll.book
                    LEFT JOIN languages l ON bll.lang_code = l.id
                    LEFT JOIN comments c ON b.id = c.book
                    LEFT JOIN books_tags_link btl ON b.id = btl.book
                    LEFT JOIN tags t ON btl.tag = t.id
                    WHERE b.id = ?
                    GROUP BY b.id, b.title, b.sort, b.pubdate, b.series_index,
                             s.name, s.sort, l.lang_code, c.text
                """

                cursor.execute(query, (self.id,))
                result = cursor.fetchone()

                if not result:
                    raise NotFoundError('book', str(self.id), 'ID')

                # Assign values from query result
                self._assign_book_data(result)

        except sqlite3.Error as e:
            raise DatabaseError(
                f'Failed to load book data for ID {self.id}: {e}',
                'book_data_loading'
            )

    def _assign_book_data(self, result: sqlite3.Row) -> None:
        """
        Assign book data from database result to instance attributes.

        Parameters
        ----------
        result : sqlite3.Row
            Database query result row.
        """
        self.title = result[0] or ''
        self.title_sort = result[1] or ''
        self.date = result[2] or ''
        self.series_idx = result[3] or 0.0
        self.author = self._clean_concatenated_string(result[4])
        self.author_sort = self._clean_concatenated_string(result[5])
        self.series = result[6] or ''
        self.series_sort = result[7] or ''
        self.publisher = self._clean_concatenated_string(result[8])
        self.identifiers = self._clean_identifiers(result[9])
        self.language = result[10] or ''
        self.synopsis = result[11] or ''
        self.tags = self._clean_concatenated_string(result[12])

    def _clean_concatenated_string(self, value: Optional[str]) -> str:
        """
        Clean concatenated string values from GROUP_CONCAT.

        Parameters
        ----------
        value : str or None
            The concatenated string value.

        Returns
        -------
        str
            Cleaned string with proper separators.
        """
        if not value:
            return ''
        return value.replace(',', ' & ')

    def _clean_identifiers(self, value: Optional[str]) -> str:
        """
        Clean identifier strings with proper formatting.

        Parameters
        ----------
        value : str or None
            The concatenated identifier string.

        Returns
        -------
        str
            Cleaned identifiers with proper separators.
        """
        if not value:
            return ''
        return value.replace(',', ', ')

    def to_json(self) -> Dict[str, Any]:
        """
        Return the book as a JSON-compatible dictionary.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing all book metadata.
        """
        return {
            'id': self.id,
            'title': self.title,
            'title_sort': self.title_sort,
            'date': self.date,
            'author': self.author,
            'author_sort': self.author_sort,
            'series': self.series,
            'series_sort': self.series_sort,
            'series_idx': self.series_idx,
            'publisher': self.publisher,
            'identifiers': self.identifiers,
            'language': self.language,
            'tags': self.tags,
            'synopsis': self.synopsis
        }

    def __str__(self) -> str:
        """
        Return a string representation of the book.

        Returns
        -------
        str
            Human-readable string representation.
        """
        return (
            f"Book(id={self.id}, title='{self.title}', "
            f"author='{self.author}')"
        )

    def __repr__(self) -> str:
        """
        Return a detailed string representation for debugging.

        Returns
        -------
        str
            Detailed string representation.
        """
        return (
            f"Book(id={self.id}, title='{self.title}', "
            f"author='{self.author}', series='{self.series}')"
        )


class CalibreDB:
    """
    Class to manage SQLite operations for Calibre database.

    This class provides all database operations needed to search and
    retrieve book metadata from a Calibre library database.
    """

    def __init__(
        self,
        library_path: str,
        db_filename: str = 'metadata.db'
    ) -> None:
        """
        Initialize CalibreDB with the path to the Calibre library.

        Parameters
        ----------
        library_path : str
            Path to the Calibre library folder.
        db_filename : str, optional
            Name of the SQLite database file, by default 'metadata.db'.

        Raises
        ------
        ConfigurationError
            If library_path is empty or invalid.
        DatabaseError
            If the database file doesn't exist.
        """
        if not library_path or not isinstance(library_path, str):
            raise ConfigurationError(
                'Library path must be a non-empty string',
                'library_path'
            )

        self.library_path = library_path
        self.db_path = os.path.join(library_path, db_filename)

        # Validate database exists
        if not os.path.exists(self.db_path):
            raise DatabaseError(
                f'Database file not found: {self.db_path}',
                'initialization'
            )

        logger.info(f'CalibreDB initialized with database: {self.db_path}')

    def _execute_search_query(
        self,
        query: str,
        params: tuple,
        operation: str
    ) -> List[tuple]:
        """
        Execute a search query with error handling.

        Parameters
        ----------
        query : str
            SQL query to execute.
        params : tuple
            Query parameters.
        operation : str
            Description of the operation for error messages.

        Returns
        -------
        List[tuple]
            Query results.

        Raises
        ------
        DatabaseError
            If there's a database error during query execution.
        """
        try:
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()

        except sqlite3.Error as e:
            raise DatabaseError(
                f'Query execution failed: {e}',
                operation
            )

    def search_books_by_title(
        self,
        title_pattern: str
    ) -> List[Tuple[int, str]]:
        """
        Search for books by title matching a pattern.

        Parameters
        ----------
        title_pattern : str
            Pattern to search for in titles (supports % wildcards).

        Returns
        -------
        List[Tuple[int, str]]
            List of (book_id, title) tuples.

        Raises
        ------
        ValidationError
            If pattern is empty or invalid.
        DatabaseError
            If there is a database error.
        """
        validated_pattern = validate_search_parameters(title_pattern)

        query = 'SELECT id, title FROM books WHERE title LIKE ? ORDER BY title'
        results = self._execute_search_query(
            query,
            (validated_pattern,),
            'title search'
        )

        if not results:
            raise NotFoundError(
                'books', validated_pattern, 'title pattern'
            )

        return results

    def search_authors_by_name(
        self,
        name_pattern: str
    ) -> List[Tuple[int, str]]:
        """
        Search for authors by name matching a pattern.

        Parameters
        ----------
        name_pattern : str
            Pattern to search for in names (supports % wildcards).

        Returns
        -------
        List[Tuple[int, str]]
            List of (author_id, name) tuples.

        Raises
        ------
        ValidationError
            If pattern is empty or invalid.
        DatabaseError
            If there is a database error.
        """
        validated_pattern = validate_search_parameters(name_pattern)

        query = 'SELECT id, name FROM authors WHERE name LIKE ? ORDER BY name'
        results = self._execute_search_query(
            query,
            (validated_pattern,),
            'author name search'
        )

        if not results:
            raise NotFoundError(
                'authors', validated_pattern, 'name pattern'
            )

        return results

    def search_books_by_tag(
        self,
        tag_pattern: str
    ) -> List[Tuple[int, str, str, str]]:
        """
        Get detailed information about books with tags matching a pattern.

        Parameters
        ----------
        tag_pattern : str
            Pattern to search for in tag names (supports % wildcards).

        Returns
        -------
        List[Tuple[int, str, str, str]]
            List of (book_id, title, author_name, publication_date) tuples,
            ordered by title.

        Raises
        ------
        ValidationError
            If pattern is empty or invalid.
        DatabaseError
            If there is a database error.
        """
        validated_pattern = validate_search_parameters(tag_pattern, 100)

        query = """
            SELECT DISTINCT b.id, b.title,
                   COALESCE(GROUP_CONCAT(a.name, ' & '), '') as authors,
                   b.pubdate
            FROM books b
            JOIN books_tags_link btl ON b.id = btl.book
            JOIN tags t ON btl.tag = t.id
            LEFT JOIN books_authors_link bal ON b.id = bal.book
            LEFT JOIN authors a ON bal.author = a.id
            WHERE t.name LIKE ?
            GROUP BY b.id, b.title, b.pubdate
            ORDER BY b.title
        """

        results = self._execute_search_query(
            query,
            (validated_pattern,),
            'tag pattern search'
        )

        if not results:
            raise NotFoundError(
                'books', validated_pattern, 'tag pattern'
            )

        return results

    def get_books_by_author(
        self,
        author_name: str
    ) -> List[Tuple[int, str, str, str]]:
        """
        Get detailed information about all books by a specific author.

        Parameters
        ----------
        author_name : str
            Name of the author.

        Returns
        -------
        List[Tuple[int, str, str, str]]
            List of (book_id, title, publication_date, series_info) tuples,
            ordered by publication date.

        Raises
        ------
        ValidationError
            If author name is empty or invalid.
        DatabaseError
            If there is a database error.
        """
        validated_name = validate_search_parameters(author_name)

        query = """
            SELECT DISTINCT b.id, b.title, b.pubdate,
                   CASE
                       WHEN s.name IS NOT NULL
                       THEN s.name || ' #' || CAST(b.series_index AS TEXT)
                       ELSE ''
                   END as series_info
            FROM books b
            JOIN books_authors_link bal ON b.id = bal.book
            JOIN authors a ON bal.author = a.id
            LEFT JOIN books_series_link bsl ON b.id = bsl.book
            LEFT JOIN series s ON bsl.series = s.id
            WHERE a.name = ?
            ORDER BY b.pubdate DESC, b.title
        """

        results = self._execute_search_query(
            query,
            (validated_name,),
            'author books search'
        )

        if not results:
            raise NotFoundError('books', validated_name, 'author name')

        return results

    def get_books_by_author_id(
        self,
        author_id: int
    ) -> List[Tuple[int, str, str, str]]:
        """
        Get detailed information about all books by a specific author ID.

        Parameters
        ----------
        author_id : int
            ID of the author.

        Returns
        -------
        List[Tuple[int, str, str, str]]
            List of (book_id, title, publication_date, series_info) tuples,
            ordered by publication date.

        Raises
        ------
        ValidationError
            If author_id is not a positive integer.
        DatabaseError
            If there is a database error.
        """
        validated_id = validate_positive_integer(author_id, 'author_id')

        query = """
            SELECT DISTINCT b.id, b.title, b.pubdate,
                   CASE
                       WHEN s.name IS NOT NULL
                       THEN s.name || ' #' || CAST(b.series_index AS TEXT)
                       ELSE ''
                   END as series_info
            FROM books b
            JOIN books_authors_link bal ON b.id = bal.book
            LEFT JOIN books_series_link bsl ON b.id = bsl.book
            LEFT JOIN series s ON bsl.series = s.id
            WHERE bal.author = ?
            ORDER BY b.pubdate DESC, b.title
        """

        results = self._execute_search_query(
            query,
            (validated_id,),
            'author ID books search'
        )

        if not results:
            raise NotFoundError('books', str(validated_id), 'author ID')

        return results

    def get_books_by_series(
        self,
        series_name: str
    ) -> List[Tuple[int, str, float]]:
        """
        Get all books in a specific series.

        Parameters
        ----------
        series_name : str
            Name of the series.

        Returns
        -------
        List[Tuple[int, str, float]]
            List of (book_id, title, series_index) tuples,
            ordered by series index.

        Raises
        ------
        ValidationError
            If series name is empty or invalid.
        DatabaseError
            If there is a database error.
        """
        validated_name = validate_search_parameters(series_name)

        query = """
            SELECT b.id, b.title, b.series_index
            FROM books b
            JOIN books_series_link bsl ON b.id = bsl.book
            JOIN series s ON bsl.series = s.id
            WHERE s.name = ?
            ORDER BY b.series_index
        """

        results = self._execute_search_query(
            query,
            (validated_name,),
            'series books search'
        )

        if not results:
            raise NotFoundError('books', validated_name, 'series name')

        return results

    def get_books_by_tag(
        self,
        tag_name: str
    ) -> List[Tuple[int, str, str, str]]:
        """
        Get detailed information about all books with a specific tag.

        Parameters
        ----------
        tag_name : str
            Name of the tag to search for.

        Returns
        -------
        List[Tuple[int, str, str, str]]
            List of (book_id, title, author_name, publication_date) tuples,
            ordered by title.

        Raises
        ------
        ValidationError
            If tag name is empty or invalid.
        DatabaseError
            If there is a database error.
        """
        validated_name = validate_search_parameters(tag_name, 100)

        query = """
            SELECT DISTINCT b.id, b.title,
                   COALESCE(GROUP_CONCAT(a.name, ' & '), '') as authors,
                   b.pubdate
            FROM books b
            JOIN books_tags_link btl ON b.id = btl.book
            JOIN tags t ON btl.tag = t.id
            LEFT JOIN books_authors_link bal ON b.id = bal.book
            LEFT JOIN authors a ON bal.author = a.id
            WHERE t.name = ?
            GROUP BY b.id, b.title, b.pubdate
            ORDER BY b.title
        """

        results = self._execute_search_query(
            query,
            (validated_name,),
            'tag books search'
        )

        if not results:
            raise NotFoundError('books', validated_name, 'tag name')

        return results

    def get_all_tags(self) -> List[Tuple[int, str]]:
        """
        Get all available tags in the database.

        Returns
        -------
        List[Tuple[int, str]]
            List of (tag_id, tag_name) tuples, ordered alphabetically by name.

        Raises
        ------
        DatabaseError
            If there is a database error.
        """
        query = 'SELECT t.id, t.name FROM tags t ORDER BY t.name'

        return self._execute_search_query(
            query,
            (),
            'get all tags'
        )

    def get_book_count(self) -> int:
        """
        Get the total number of books in the database.

        Returns
        -------
        int
            Total number of books.

        Raises
        ------
        DatabaseError
            If there is a database error.
        """
        query = 'SELECT COUNT(*) FROM books'

        results = self._execute_search_query(
            query,
            (),
            'book count'
        )

        return int(results[0][0]) if results else 0

    def get_author_count(self) -> int:
        """
        Get the total number of authors in the database.

        Returns
        -------
        int
            Total number of authors.

        Raises
        ------
        DatabaseError
            If there is a database error.
        """
        query = 'SELECT COUNT(*) FROM authors'

        results = self._execute_search_query(
            query,
            (),
            'author count'
        )

        return int(results[0][0]) if results else 0

    def get_database_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the database.

        Returns
        -------
        Dict[str, Any]
            Dictionary containing database statistics and information.

        Raises
        ------
        DatabaseError
            If there is a database error.
        """
        try:
            info = {
                'db_path': self.db_path,
                'library_path': self.library_path,
                'books_count': self.get_book_count(),
                'authors_count': self.get_author_count(),
            }

            # Get additional counts in a single connection
            with database_connection(self.db_path) as conn:
                cursor = conn.cursor()

                # Get series count
                cursor.execute('SELECT COUNT(*) FROM series')
                info['series_count'] = cursor.fetchone()[0]

                # Get publishers count
                cursor.execute('SELECT COUNT(*) FROM publishers')
                info['publishers_count'] = cursor.fetchone()[0]

                # Get tags count
                cursor.execute('SELECT COUNT(*) FROM tags')
                info['tags_count'] = cursor.fetchone()[0]

                # Get languages count
                cursor.execute('SELECT COUNT(*) FROM languages')
                info['languages_count'] = cursor.fetchone()[0]

            return info

        except sqlite3.Error as e:
            raise DatabaseError(
                f'Failed to retrieve database information: {e}',
                'database info'
            )
