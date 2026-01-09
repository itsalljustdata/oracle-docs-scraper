#!/usr/bin/env python3
"""
SQL Converter utility for Oracle to Databricks SQL conversion
"""

import sqlglot
from sqlglot import optimizer
import logging

class WarningAsExceptionHandler(logging.Handler):
    """Custom logging handler that raises exceptions for WARNING level messages"""
    def emit(self, record):
        # if record.levelno >= logging.WARNING:
        raise Exception(record.getMessage())

def extract_table_names(sql: str) -> list:
    """Extract all table names from a SQL query"""
    try:
        parsed = sqlglot.parse_one(sql, dialect="oracle")
        tables = []
        
        # Find all table references
        for table in parsed.find_all(sqlglot.expressions.Table):
            table_name = table.name
            alias = table.alias if table.alias else None
            thisTab = {
                'name': table_name
                # 'full_name': f"{table_name} {alias}" if alias else table_name
            }
            if alias:
                thisTab['alias'] = alias
            tables.append(thisTab)
        
        return tables
    except Exception as e:
        return [f"Error parsing SQL: {e}"]

def convert_single_query(oracle_sql: str) -> dict:
    """Convert a single Oracle SQL query to Databricks format"""
    result = {
        'original': oracle_sql,
    }
    
    if not oracle_sql or not oracle_sql.strip():
        return result
    
    # Set up custom handler to convert warnings to exceptions
    sqlglot_logger = logging.getLogger('sqlglot')
    original_handlers = sqlglot_logger.handlers.copy()
    
    # Add our custom handler and set level to capture warnings
    warning_handler = WarningAsExceptionHandler()
    sqlglot_logger.handlers.clear()
    sqlglot_logger.addHandler(warning_handler)
    
    try:
        # Step 1: Convert Oracle legacy syntax to Oracle ANSI
        parsed = sqlglot.parse_one(oracle_sql, dialect="oracle")
        optimized = parsed.transform(optimizer.optimize)
        oracle_ansi = optimized.sql(dialect="oracle", pretty=True)
        
        # Step 2: Convert Oracle ANSI to Databricks
        databricks_sql = sqlglot.transpile(
            oracle_ansi, 
            read="oracle", 
            write="databricks",
            pretty=True,
            error_level=sqlglot.ErrorLevel.RAISE
        )[0]
        result['pretty'] = oracle_ansi
        result['converted'] = databricks_sql
    except Exception as e:
        result['error'] = str(e)
    finally:
        # Restore original logging configuration
        sqlglot_logger.handlers.clear()
        sqlglot_logger.handlers.extend(original_handlers)
    
    return result


if __name__ == "__main__":
    # Example usage
    sample_sql = "SELECT\n  \"ps\".\"payment_schedule_id\" AS \"payment_schedule_id\",\n  \"ps\".\"customer_trx_id\" AS \"customer_trx_id\",\n  \"cst\".\"party_id\" AS \"party_id\",\n  \"cst\".\"cust_account_id\" AS \"cust_account_id\",\n  \"ps\".\"class\" AS \"class\",\n  \"ps\".\"status\" AS \"status\",\n  \"ps\".\"amount_due_original\" AS \"amount_due_original\",\n  \"ps\".\"amount_due_remaining\" AS \"amount_due_remaining\",\n  \"ps\".\"trx_date\" AS \"trx_date\",\n  \"ps\".\"gl_date\" AS \"gl_date\",\n  DECODE(\"ps\".\"customer_id\", -1, '', -2, '', -3, '', \"ps\".\"due_date\") AS \"_col_10\"\nFROM \"hz_cust_accounts\" \"cst\"\nJOIN \"ar_payment_schedules\" \"ps\"\n  ON \"cst\".\"cust_account_id\" (+) = \"ps\".\"customer_id\"\n  AND \"ps\".\"amount_due_remaining\" > 0\n  AND (\n    \"ps\".\"amount_due_remaining\" > ABS(\"ps\".\"amount_in_dispute\")\n    OR \"ps\".\"amount_in_dispute\" IS NULL\n  )\n  AND \"ps\".\"class\" IN ('DM', 'INV', 'CB')\n  AND \"ps\".\"due_date\" < TRUNC(SYSDATE, 'DD')\n  AND \"ps\".\"selected_for_receipt_batch_id\" IS NULL\n  AND \"ps\".\"status\" = 'OP'\n  AND NVL(\"ps\".\"exclude_from_dunning_flag\", 'N') <> 'C'"
    print(sample_sql)
    conversion_result = convert_single_query(sample_sql)
    for k,v in conversion_result.items():
        print(f"--- {k} ---")
        print(v)
        print()