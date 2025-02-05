import pandas as pd
import sqlparse
import re

# Hardcoded input and output files
INPUT_SQL_FILE = "0_to_be_convert.sql"
OUTPUT_XLSX_FILE = "1_insert_data.xlsx"

def extract_insert_data(sql_statement):
    # Extract table name from INSERT statement
    table_name = re.search(r"INSERT INTO [`]?(\w+)[`]?", sql_statement, re.IGNORECASE)
    if not table_name:
        return None, None
    
    table_name = table_name.group(1)
    print(f"Processing table: {table_name}")
    
    # Extract all value groups - Modified to handle multiple VALUES sections
    # Updated pattern to better handle multiple INSERT VALUES
    values_pattern = r'VALUES?\s*(\((?:[^()]|\([^()]*\))*\)(?:\s*,\s*\((?:[^()]|\([^()]*\))*\))*)'
    values_match = re.search(values_pattern, sql_statement, re.IGNORECASE | re.DOTALL)
    
    if not values_match:
        # Try alternate pattern for different VALUES format
        values_pattern = r'VALUES?\s*(\([^;]+\)(?:\s*,\s*\([^;]+\))*)'
        values_match = re.search(values_pattern, sql_statement, re.IGNORECASE | re.DOTALL)
        if not values_match:
            print(f"No values found for table {table_name}")
            return None, None
    
    # Get the values section and normalize whitespace
    values_section = values_match.group(1)
    values_section = re.sub(r'\s+', ' ', values_section)
    
    # Split into individual value groups
    value_groups = []
    current_group = []
    buffer = ''
    in_quotes = False
    paren_level = 0
    
    for char in values_section:
        if char == "'" and not in_quotes:
            in_quotes = True
            buffer += char
        elif char == "'" and in_quotes:
            in_quotes = False
            buffer += char
        elif char == '(' and not in_quotes:
            paren_level += 1
            if paren_level == 1:
                buffer = ''
            else:
                buffer += char
        elif char == ')' and not in_quotes:
            paren_level -= 1
            if paren_level == 0:
                if buffer:
                    current_group.append(buffer.strip())
                if current_group:
                    value_groups.append(current_group)
                current_group = []
            else:
                buffer += char
        elif char == ',' and not in_quotes:
            if paren_level == 0:
                continue
            if paren_level == 1:
                if buffer.strip():
                    current_group.append(buffer.strip())
                buffer = ''
            else:
                buffer += char
        else:
            buffer += char

    # Clean values and create rows
    cleaned_rows = []
    for group in value_groups:
        cleaned_row = []
        for val in group:
            # Remove leading/trailing quotes and spaces
            val = val.strip()
            if val.lower() == 'null':
                val = None
            elif (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                # Keep semicolons and other special characters within quotes
                val = val[1:-1]  # Remove quotes but preserve content including semicolons
            cleaned_row.append(val)
        if cleaned_row:  # Only append non-empty rows
            cleaned_rows.append(cleaned_row)

    # Create DataFrame
    if cleaned_rows:
        df = pd.DataFrame(cleaned_rows)
    else:
        return None, None

    # Try to extract column names
    columns_match = re.search(r"INSERT INTO.*?\((.*?)\)\s*VALUES?", sql_statement, re.IGNORECASE | re.DOTALL)
    if columns_match:
        columns = [col.strip().strip('`').strip('"') for col in columns_match.group(1).split(',')]
        if len(columns) == len(df.columns):
            df.columns = columns
            print(f"Found {len(columns)} columns for table {table_name}")
        else:
            print(f"Column mismatch for {table_name}: {len(columns)} names but {len(df.columns)} values")
    
    print(f"Extracted {len(cleaned_rows)} rows for table {table_name}")
    return table_name, df

def main():
    # Read SQL file
    print(f"Reading SQL file: {INPUT_SQL_FILE}")
    with open(INPUT_SQL_FILE, 'r', encoding='utf-8') as file:
        sql_content = file.read()
    
    # Parse SQL content and combine INSERT statements for the same table
    statements = sqlparse.split(sql_content)
    print(f"Found {len(statements)} SQL statements")
    
    # Dictionary to store DataFrames for each table
    tables_data = {}
    
    # Process each statement
    for i, statement in enumerate(statements):
        print(f"\nProcessing statement {i+1}/{len(statements)}")
        if 'INSERT INTO' in statement.upper():
            table_name, df = extract_insert_data(statement)
            if table_name and df is not None and not df.empty:
                if table_name in tables_data:
                    # Concatenate with existing data for the same table
                    print(f"Appending {len(df)} rows to existing table {table_name}")
                    tables_data[table_name] = pd.concat([tables_data[table_name], df], ignore_index=True)
                else:
                    tables_data[table_name] = df
    
    # Add debug print
    for statement in statements:
        if 'INSERT INTO `master_data_supplier`' in statement:
            print("Found master_data_supplier insert statement:")
            print(statement[:200])  # Print first 200 chars for debugging
            table_name, df = extract_insert_data(statement)
            if df is not None:
                print(f"Extracted {len(df)} rows")
            else:
                print("Failed to extract data")
    
    # Write all tables to Excel
    print(f"\nWriting {len(tables_data)} tables to Excel")
    with pd.ExcelWriter(OUTPUT_XLSX_FILE, engine='xlsxwriter') as writer:
        for table_name, df in tables_data.items():
            # Remove duplicates before writing
            df = df.drop_duplicates()
            df.to_excel(writer, sheet_name=table_name, index=False)
            print(f"Wrote table: {table_name} with {len(df)} rows")

if __name__ == "__main__":
    main()
    print(f"\nConversion completed! File saved as {OUTPUT_XLSX_FILE}")
