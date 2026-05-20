#!/usr/bin/env python3
"""
Check table value ranges - compute statistics for all columns in a table.

All columns: total_count, non_null_count, distinct_count, nulls, zeros_or_empty
For numeric columns: min, max, avg, percentiles (10, 30, 50, 70, 90)
For string columns: length stats (min, max, avg, percentiles)
For date columns: min, max (as timestamps)

Supports:
- DuckDB databases (.duckdb, .db)
- SQLite databases (.sqlite, .sqlite3)
- CSV files (.csv)
- Parquet files (.parquet)
- JSON/NDJSON files (.json, .ndjson)

Usage:
  python check_table_value_ranges.py <source> [options]

Examples:
  python check_table_value_ranges.py stocks.duckdb --table daily_bars_adjusted
  python check_table_value_ranges.py data.csv
  python check_table_value_ranges.py data.parquet
  python check_table_value_ranges.py stocks.sqlite --table prices

Options:
  --table, -t       Table name (required for database sources)
  --columns, -c     Comma-separated list of columns to analyze (default: all)
  --output, -o      Output format: table (default), csv, json
  --limit, -l       Limit number of rows to analyze (for large files)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    import duckdb
except ImportError:
    print("Error: Python package 'duckdb' is not installed. pip install duckdb", file=sys.stderr)
    raise SystemExit(1)


def get_source_type(source: str) -> str:
    """Determine the type of data source."""
    path = Path(source)
    suffix = path.suffix.lower()

    if suffix in ('.duckdb', '.db'):
        return 'duckdb'
    elif suffix in ('.sqlite', '.sqlite3'):
        return 'sqlite'
    elif suffix == '.csv':
        return 'csv'
    elif suffix == '.parquet':
        return 'parquet'
    elif suffix in ('.json', '.ndjson'):
        return 'json'
    else:
        # Try to detect by content or default to duckdb
        return 'duckdb'


def create_connection(source: str, source_type: str, table: Optional[str] = None) -> tuple:
    """Create a DuckDB connection and return (connection, table_name)."""
    con = duckdb.connect(':memory:')

    if source_type == 'duckdb':
        con.execute(f"ATTACH '{source}' AS src (READ_ONLY)")
        if table:
            return con, f"src.{table}"
        else:
            # List available tables
            tables = con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='src' OR table_catalog='src'"
            ).fetchall()
            if not tables:
                tables = con.execute(
                    "SELECT name FROM src.sqlite_master WHERE type='table'"
                ).fetchall()
            raise ValueError(f"Please specify a table with --table. Available: {[t[0] for t in tables]}")

    elif source_type == 'sqlite':
        con.execute(f"ATTACH '{source}' AS src (TYPE SQLITE, READ_ONLY)")
        if table:
            return con, f"src.{table}"
        else:
            tables = con.execute("SELECT name FROM src.sqlite_master WHERE type='table'").fetchall()
            raise ValueError(f"Please specify a table with --table. Available: {[t[0] for t in tables]}")

    elif source_type == 'csv':
        table_name = "data"
        con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_csv_auto('{source}')")
        return con, table_name

    elif source_type == 'parquet':
        table_name = "data"
        con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{source}')")
        return con, table_name

    elif source_type == 'json':
        table_name = "data"
        con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM read_json_auto('{source}')")
        return con, table_name

    else:
        raise ValueError(f"Unsupported source type: {source_type}")


def get_column_info(con: duckdb.DuckDBPyConnection, table: str) -> List[Dict[str, str]]:
    """Get column names and types from a table."""
    # Handle qualified table names
    if '.' in table:
        schema, tbl = table.rsplit('.', 1)
        query = f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{tbl}'"
    else:
        query = f"DESCRIBE {table}"

    try:
        result = con.execute(query).fetchall()
        if '.' in table:
            return [{'name': row[0], 'type': row[1]} for row in result]
        else:
            return [{'name': row[0], 'type': row[1]} for row in result]
    except Exception:
        # Fallback: use PRAGMA for SQLite-attached databases
        result = con.execute(f"PRAGMA table_info({table})").fetchall()
        return [{'name': row[1], 'type': row[2]} for row in result]


def classify_column_type(dtype: str) -> str:
    """Classify a column type into numeric, string, date, or other."""
    dtype_upper = dtype.upper()

    if any(t in dtype_upper for t in ['INT', 'FLOAT', 'DOUBLE', 'DECIMAL', 'NUMERIC', 'REAL', 'BIGINT', 'SMALLINT', 'TINYINT']):
        return 'numeric'
    elif any(t in dtype_upper for t in ['VARCHAR', 'CHAR', 'TEXT', 'STRING']):
        return 'string'
    elif any(t in dtype_upper for t in ['DATE', 'TIME', 'TIMESTAMP']):
        return 'date'
    elif 'BOOL' in dtype_upper:
        return 'boolean'
    else:
        return 'other'


def generate_stats_query(table: str, columns: List[Dict[str, str]]) -> str:
    """Generate a SQL query to compute statistics for all columns."""

    numeric_cols = [c for c in columns if classify_column_type(c['type']) == 'numeric']
    string_cols = [c for c in columns if classify_column_type(c['type']) == 'string']
    date_cols = [c for c in columns if classify_column_type(c['type']) == 'date']
    bool_cols = [c for c in columns if classify_column_type(c['type']) == 'boolean']
    other_cols = [c for c in columns if classify_column_type(c['type']) == 'other']

    unions = []

    # Numeric columns
    for col in numeric_cols:
        name = col['name']
        dtype = col['type']
        unions.append(f"""
        SELECT
            'numeric' as category,
            '{name}' as column_name,
            '{dtype}' as data_type,
            COUNT(DISTINCT "{name}") as distinct_count,
            SUM(CASE WHEN "{name}" IS NULL THEN 1 ELSE 0 END) as nulls,
            SUM(CASE WHEN "{name}" = 0 THEN 1 ELSE 0 END) as zeros_or_empty,
            MIN("{name}")::DOUBLE as min_val,
            MAX("{name}")::DOUBLE as max_val,
            AVG("{name}")::DOUBLE as avg_val,
            PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY "{name}") as p10,
            PERCENTILE_CONT(0.30) WITHIN GROUP (ORDER BY "{name}") as p30,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY "{name}") as p50,
            PERCENTILE_CONT(0.70) WITHIN GROUP (ORDER BY "{name}") as p70,
            PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY "{name}") as p90
        FROM {table}
        """)

    # String columns (min/max/avg/percentiles are for LENGTH)
    for col in string_cols:
        name = col['name']
        dtype = col['type']
        unions.append(f"""
        SELECT
            'string' as category,
            '{name}' as column_name,
            '{dtype}' as data_type,
            COUNT(DISTINCT "{name}") as distinct_count,
            SUM(CASE WHEN "{name}" IS NULL THEN 1 ELSE 0 END) as nulls,
            SUM(CASE WHEN "{name}" = '' THEN 1 ELSE 0 END) as zeros_or_empty,
            MIN(LENGTH("{name}"))::DOUBLE as min_val,
            MAX(LENGTH("{name}"))::DOUBLE as max_val,
            AVG(LENGTH("{name}"))::DOUBLE as avg_val,
            PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY LENGTH("{name}")) as p10,
            PERCENTILE_CONT(0.30) WITHIN GROUP (ORDER BY LENGTH("{name}")) as p30,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY LENGTH("{name}")) as p50,
            PERCENTILE_CONT(0.70) WITHIN GROUP (ORDER BY LENGTH("{name}")) as p70,
            PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY LENGTH("{name}")) as p90
        FROM {table}
        """)

    # Date columns
    for col in date_cols:
        name = col['name']
        dtype = col['type']
        unions.append(f"""
        SELECT
            'date' as category,
            '{name}' as column_name,
            '{dtype}' as data_type,
            COUNT(DISTINCT "{name}") as distinct_count,
            SUM(CASE WHEN "{name}" IS NULL THEN 1 ELSE 0 END) as nulls,
            0 as zeros_or_empty,
            EXTRACT(EPOCH FROM MIN("{name}"))::DOUBLE as min_val,
            EXTRACT(EPOCH FROM MAX("{name}"))::DOUBLE as max_val,
            NULL::DOUBLE as avg_val,
            NULL::DOUBLE as p10,
            NULL::DOUBLE as p30,
            NULL::DOUBLE as p50,
            NULL::DOUBLE as p70,
            NULL::DOUBLE as p90
        FROM {table}
        """)

    # Boolean columns
    for col in bool_cols:
        name = col['name']
        dtype = col['type']
        unions.append(f"""
        SELECT
            'boolean' as category,
            '{name}' as column_name,
            '{dtype}' as data_type,
            COUNT(DISTINCT "{name}") as distinct_count,
            SUM(CASE WHEN "{name}" IS NULL THEN 1 ELSE 0 END) as nulls,
            SUM(CASE WHEN "{name}" = FALSE THEN 1 ELSE 0 END) as zeros_or_empty,
            MIN("{name}"::INT)::DOUBLE as min_val,
            MAX("{name}"::INT)::DOUBLE as max_val,
            AVG("{name}"::INT)::DOUBLE as avg_val,
            NULL::DOUBLE as p10,
            NULL::DOUBLE as p30,
            NULL::DOUBLE as p50,
            NULL::DOUBLE as p70,
            NULL::DOUBLE as p90
        FROM {table}
        """)

    # Other columns
    for col in other_cols:
        name = col['name']
        dtype = col['type']
        unions.append(f"""
        SELECT
            'other' as category,
            '{name}' as column_name,
            '{dtype}' as data_type,
            COUNT(DISTINCT "{name}") as distinct_count,
            SUM(CASE WHEN "{name}" IS NULL THEN 1 ELSE 0 END) as nulls,
            0 as zeros_or_empty,
            NULL::DOUBLE as min_val,
            NULL::DOUBLE as max_val,
            NULL::DOUBLE as avg_val,
            NULL::DOUBLE as p10,
            NULL::DOUBLE as p30,
            NULL::DOUBLE as p50,
            NULL::DOUBLE as p70,
            NULL::DOUBLE as p90
        FROM {table}
        """)

    if not unions:
        raise ValueError("No columns found in table")

    query = "UNION ALL".join(unions)

    # Wrap in formatting query
    final_query = f"""
    WITH stats AS (
        {query}
    )
    SELECT
        column_name,
        data_type,
        distinct_count,
        nulls,
        zeros_or_empty,
        CASE
            WHEN category = 'date' AND min_val IS NOT NULL THEN CAST(TO_TIMESTAMP(min_val) AS VARCHAR)
            WHEN min_val IS NULL THEN NULL
            WHEN ABS(min_val) >= 1e9 THEN PRINTF('%.3e', min_val)
            WHEN ABS(min_val) < 0.0001 AND min_val != 0 THEN PRINTF('%.3e', min_val)
            ELSE PRINTF('%.6g', min_val)
        END as min,
        CASE
            WHEN category = 'date' AND max_val IS NOT NULL THEN CAST(TO_TIMESTAMP(max_val) AS VARCHAR)
            WHEN max_val IS NULL THEN NULL
            WHEN ABS(max_val) >= 1e9 THEN PRINTF('%.3e', max_val)
            ELSE PRINTF('%.6g', max_val)
        END as max,
        CASE
            WHEN avg_val IS NULL THEN NULL
            WHEN ABS(avg_val) >= 1e9 THEN PRINTF('%.3e', avg_val)
            ELSE PRINTF('%.6g', avg_val)
        END as avg,
        CASE WHEN p10 IS NULL THEN NULL ELSE PRINTF('%.6g', p10) END as p10,
        CASE WHEN p30 IS NULL THEN NULL ELSE PRINTF('%.6g', p30) END as p30,
        CASE WHEN p50 IS NULL THEN NULL ELSE PRINTF('%.6g', p50) END as p50,
        CASE WHEN p70 IS NULL THEN NULL ELSE PRINTF('%.6g', p70) END as p70,
        CASE WHEN p90 IS NULL THEN NULL ELSE PRINTF('%.6g', p90) END as p90
    FROM stats
    ORDER BY
        CASE category
            WHEN 'numeric' THEN 1
            WHEN 'string' THEN 2
            WHEN 'date' THEN 3
            WHEN 'boolean' THEN 4
            ELSE 5
        END,
        column_name
    """

    return final_query


def format_output(results: List[tuple], columns: List[str], output_format: str) -> str:
    """Format the results based on output format."""

    if output_format == 'json':
        data = [dict(zip(columns, row)) for row in results]
        return json.dumps(data, indent=2, default=str)

    elif output_format == 'csv':
        lines = [','.join(columns)]
        for row in results:
            lines.append(','.join(str(v) if v is not None else '' for v in row))
        return '\n'.join(lines)

    else:  # table format
        # Calculate column widths
        widths = [len(c) for c in columns]
        for row in results:
            for i, val in enumerate(row):
                widths[i] = max(widths[i], len(str(val) if val is not None else ''))

        # Build table
        lines = []
        header = ' | '.join(c.ljust(widths[i]) for i, c in enumerate(columns))
        separator = '-+-'.join('-' * w for w in widths)
        lines.append(header)
        lines.append(separator)

        for row in results:
            line = ' | '.join(
                (str(v) if v is not None else '').ljust(widths[i])
                for i, v in enumerate(row)
            )
            lines.append(line)

        return '\n'.join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check table value ranges - compute statistics for all columns"
    )
    parser.add_argument("source", help="Data source (database file or data file)")
    parser.add_argument("--table", "-t", help="Table name (required for database sources)")
    parser.add_argument(
        "--columns", "-c",
        help="Comma-separated list of columns to analyze (default: all)"
    )
    parser.add_argument(
        "--output", "-o",
        choices=['table', 'csv', 'json'],
        default='table',
        help="Output format (default: table)"
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        help="Limit number of rows to analyze"
    )
    args = parser.parse_args(argv)

    # Check source exists
    if not Path(args.source).exists():
        print(f"Error: Source file not found: {args.source}", file=sys.stderr)
        return 1

    # Determine source type
    source_type = get_source_type(args.source)

    try:
        # Create connection
        con, table_name = create_connection(args.source, source_type, args.table)

        # Apply limit if specified
        if args.limit:
            limited_table = f"(SELECT * FROM {table_name} LIMIT {args.limit})"
        else:
            limited_table = table_name

        # Get row count
        row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

        # Get column info
        columns = get_column_info(con, table_name)

        # Filter columns if specified
        if args.columns:
            requested_cols = {c.strip().lower() for c in args.columns.split(',')}
            columns = [c for c in columns if c['name'].lower() in requested_cols]
            if not columns:
                print(f"Error: No matching columns found. Requested: {args.columns}", file=sys.stderr)
                return 1

        # Generate and execute stats query
        query = generate_stats_query(limited_table, columns)
        results = con.execute(query).fetchall()

        # Get result column names
        result_columns = [
            'column_name', 'data_type', 'distinct',
            'nulls', 'zeros_or_empty', 'min', 'max', 'avg', 'p10', 'p30', 'p50', 'p70', 'p90'
        ]

        # Print header info
        if args.output == 'table':
            if args.limit:
                print(f"Rows: {min(args.limit, row_count):,} (of {row_count:,} total)")
            else:
                print(f"Rows: {row_count:,}")
            print()

        # Format and print output
        output = format_output(results, result_columns, args.output)
        print(output)

        con.close()
        return 0

    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
