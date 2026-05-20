# Check Table Value Ranges

Analyze data quality and value distributions for table columns. Reports null/zero/empty counts, distinct values, and range statistics (min, max, avg, percentiles) for each column.

## How to Use This Skill

When the user asks to check table value ranges, run the Python script and then summarize the results.

### Step 1: Run the Script

```bash
python ~/.claude/skills/check-table-value-ranges/check_table_value_ranges.py <source> [options]
```

**Options:**
- `--table, -t` - Table name (required for database sources)
- `--columns, -c` - Comma-separated list of columns to analyze (default: all)
- `--output, -o` - Output format: table (default), csv, json
- `--limit, -l` - Limit number of rows to analyze (for large files)

**Supported Sources:**
- DuckDB databases (.duckdb, .db)
- SQLite databases (.sqlite, .sqlite3)
- CSV files (.csv)
- Parquet files (.parquet)
- JSON/NDJSON files (.json, .ndjson)

### Step 2: Display Results

Present the output table to the user. The table has these columns:

| Column | Description |
|--------|-------------|
| column_name | Name of the column |
| data_type | Original data type |
| distinct | Distinct value count |
| nulls | Null value count |
| zeros_or_empty | Zero count (numeric/boolean) or empty string count (string) |
| min | Minimum value (length for strings, timestamp for dates) |
| max | Maximum value (length for strings, timestamp for dates) |
| avg | Average value (length for strings, NULL for dates) |
| p10-p90 | Percentiles at 10%, 30%, 50%, 70%, 90% (NULL for dates/booleans) |

### Step 3: Summarize Findings

After showing the results, provide a summary that highlights:

**Data Quality Issues (flag these):**
- Columns with NULL values (especially if unexpected)
- Columns with many zeros or empty strings
- Low distinct count relative to total (possible data issues or categorical columns)
- Very high distinct count equal to total (possible unique identifiers)

**Value Range Concerns (flag these):**
- Negative values in columns that should be positive (e.g., prices, counts)
- Extreme outliers: large gap between p90 and max, or between min and p10
- Suspicious min/max values (e.g., prices of 0 or extremely high values)
- Date ranges that seem incorrect (future dates, very old dates)

**Notable Patterns (mention these):**
- Skewed distributions (large difference between avg and p50/median)
- Columns that appear to be identifiers vs. measures
- Date range coverage
- Any columns where all values are the same (distinct=1)

## Examples

```bash
# Check all columns in a DuckDB table
python ~/.claude/skills/check-table-value-ranges/check_table_value_ranges.py stocks.duckdb -t daily_bars

# Check specific columns only
python ~/.claude/skills/check-table-value-ranges/check_table_value_ranges.py stocks.duckdb -t daily_bars -c "open,high,low,close,volume"

# Check a CSV file with row limit
python ~/.claude/skills/check-table-value-ranges/check_table_value_ranges.py data.csv -l 10000

# Check a Parquet file
python ~/.claude/skills/check-table-value-ranges/check_table_value_ranges.py data.parquet
```
