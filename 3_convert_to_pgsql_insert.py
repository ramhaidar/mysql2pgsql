import pandas as pd
import re
from datetime import datetime

def get_column_types(sql_file):
    column_types = {}
    with open(sql_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    tables = re.findall(r'CREATE TABLE (\w+) \((.*?)\);', content, re.DOTALL)
    for table, columns in tables:
        column_types[table] = {}
        for line in columns.split('\n'):
            matches = re.search(r'\s*(\w+)\s+([\w\s\(\),]+?)(?:\s+(?:NOT NULL|DEFAULT|CHECK|PRIMARY KEY|REFERENCES|UNIQUE)|,|$)', line.strip())
            if matches:
                col_name, col_type = matches.groups()
                column_types[table][col_name] = col_type.strip().lower()
    return column_types

def is_boolean_type(col_type):
    """Check if the column type should be considered boolean."""
    if not col_type:
        return False
    # Matches any occurrence of bool, boolean, tinyint(1), or bit(1)
    return bool(re.search(r'\b(bool|boolean|tinyint\(1\)|bit\(1\))\b', col_type, re.IGNORECASE))

def format_value(value, column_type=None):
    if pd.isna(value) or str(value).lower() == 'nan' or str(value).strip() == '':
        return 'NULL'

    if column_type and is_boolean_type(column_type):
        # Convert to 'true' or 'false' if recognized as boolean
        if isinstance(value, (bool, int, float)):
            return 'true' if bool(value) else 'false'
        val_str = str(value).lower().strip()
        if val_str in ('true', 't', 'yes', 'y', '1'):
            return 'true'
        elif val_str in ('false', 'f', 'no', 'n', '0'):
            return 'false'
        return 'NULL'

    # Handle remaining types
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(int(value) if float(value).is_integer() else value)
    return "'" + str(value).replace("'", "''") + "'"

def get_table_columns(schema_file, table_name):
    """Get column names from schema file for a specific table"""
    with open(schema_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    table_match = re.search(f'CREATE TABLE {table_name} \((.*?)\);', content, re.DOTALL)
    if not table_match:
        return []
    
    columns = []
    for line in table_match.group(1).split('\n'):
        col_match = re.match(r'\s*(\w+)\s+', line.strip())
        if col_match:
            columns.append(col_match.group(1))
    
    return columns

def preprocess_excel_boolean(df, table_column_types):
    """Convert boolean values in Excel before SQL conversion"""
    for col in df.columns:
        col_type = table_column_types.get(str(col), '')
        if is_boolean_type(col_type):
            df[col] = df[col].map({
                1: True, 
                0: False,
                '1': True,
                '0': False,
                1.0: True,
                0.0: False,
                'true': True,
                'false': False,
                'yes': True,
                'no': False,
                'y': True,
                'n': False,
                True: True,
                False: False
            }, na_action='ignore')
            df[col] = df[col].map({True: "true", False: "false"}, na_action='ignore')
            df[col] = df[col].astype(str)
    return df

def get_boolean_columns(schema_file):
    """Get boolean columns from PostgreSQL schema file"""
    boolean_cols = {}
    
    with open(schema_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    current_table = None
    
    for line in content.split('\n'):
        # Check for table definition
        if 'CREATE TABLE' in line:
            current_table = line.split()[2]
            boolean_cols[current_table] = []
            continue
            
        # Look for boolean columns
        if current_table and 'boolean' in line.lower():
            # Extract column name
            col_match = re.match(r'\s*(\w+)\s+boolean', line.strip(), re.IGNORECASE)
            if col_match:
                boolean_cols[current_table].append(col_match.group(1))
                
    return boolean_cols

def preprocess_excel_file(excel_file, schema_file):
    """Preprocess Excel file to handle boolean values"""
    output_excel = '3_processed_insert_data.xlsx'
    boolean_cols = get_boolean_columns(schema_file)
    
    xl = pd.ExcelFile(excel_file)
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        for sheet in xl.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet)
            
            # Convert boolean columns if present
            if sheet in boolean_cols:
                for col in boolean_cols[sheet]:
                    if col in df.columns:
                        print(f"Converting boolean column {col} in table {sheet}")
                        df[col] = df[col].apply(lambda x: 
                            'true' if str(x).lower().strip() in ('1', 'true', 'yes', 'y', 't') 
                            else 'false'
                        )
            
            df.to_excel(writer, sheet_name=sheet, index=False)
    
    return output_excel

def generate_insert_statements(excel_file, output_file, schema_file):
    try:
        boolean_columns = get_boolean_columns(schema_file)
        column_types = get_column_types(schema_file)
        xl = pd.ExcelFile(excel_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('-- Generated PostgreSQL INSERT statements\n\n')
            
            # Write transaction begin and disable FK constraints
            f.write('-- Begin transaction\n')
            f.write('BEGIN;\n\n')
            f.write('-- Disable foreign key constraints for all tables\n')
            f.write('SET session_replication_role = \'replica\';\n\n')
            
            # Original insert statements generation
            for sheet_name in xl.sheet_names:
                print(f"\nProcessing table: {sheet_name}")
                try:
                    # Force boolean columns to be read as strings
                    converters = {col: str for col in boolean_columns.get(sheet_name, [])}
                    df = pd.read_excel(excel_file, sheet_name=sheet_name, converters=converters)
                    
                    table_column_types = column_types.get(sheet_name, {})
                    
                    schema_columns = get_table_columns(schema_file, sheet_name)
                    if schema_columns and len(schema_columns) == len(df.columns):
                        df.columns = schema_columns
                    else:
                        df.columns = [str(col) for col in df.columns]
                    
                    print("Column names:", df.columns.tolist())
                    columns = df.columns.tolist()
                    
                    f.write(f"INSERT INTO {sheet_name} ({', '.join(columns)}) VALUES\n")
                    
                    rows = []
                    for idx, row in df.iterrows():
                        row_dict = row.to_dict()
                        formatted_values = []
                        for col in columns:
                            val = row_dict[col]
                            col_type = table_column_types.get(col)
                            formatted_val = format_value(val, col_type)
                            formatted_values.append(formatted_val)
                        row_str = f"({', '.join(formatted_values)})"
                        rows.append(row_str)
                    
                    if rows:
                        f.write(',\n'.join(rows) + ';\n\n')
                
                except Exception as e:
                    print(f"Error processing sheet {sheet_name}: {str(e)}")
                    raise
            
            # Write transaction end and sequence reset code
            f.write('-- Re-enable foreign key constraints\n')
            f.write('SET session_replication_role = \'origin\';\n\n')
            f.write('-- Commit the transaction\n')
            f.write('COMMIT;\n\n')
            
            # Add sequence reset code
            f.write('-- This script generates commands to reset all sequences in the database\n')
            f.write('-- It will reset sequences based on the maximum value in each table\'s corresponding column\n\n')
            f.write('''DO $$
DECLARE
    -- Variables for storing sequence information
    sequence_record RECORD;
    max_value bigint;
    sequence_name text;
    table_name text;
    column_name text;
    set_value_query text;
BEGIN
    -- Loop through all sequences in the current schema
    FOR sequence_record IN 
        SELECT
            n.nspname as schema_name,
            t.relname as table_name,
            a.attname as column_name,
            s.relname as sequence_name
        FROM pg_class s
        JOIN pg_depend d ON d.objid = s.oid
        JOIN pg_class t ON d.refobjid = t.oid
        JOIN pg_attribute a ON (d.refobjid, d.refobjsubid) = (a.attrelid, a.attnum)
        JOIN pg_namespace n ON n.oid = s.relnamespace
        WHERE s.relkind = 'S'
        AND n.nspname = 'public'  -- Change this if you want to target a different schema
    LOOP
        -- Get the maximum value from the corresponding table column
        EXECUTE format('SELECT COALESCE(MAX(%I), 0) + 1 FROM %I.%I', 
            sequence_record.column_name,
            sequence_record.schema_name,
            sequence_record.table_name
        ) INTO max_value;

        -- Set the sequence value
        EXECUTE format(
            'ALTER SEQUENCE %I.%I RESTART WITH %s',
            sequence_record.schema_name,
            sequence_record.sequence_name,
            max_value
        );

        RAISE NOTICE 'Reset sequence %.% for column % to %',
            sequence_record.schema_name,
            sequence_record.sequence_name,
            sequence_record.column_name,
            max_value;
    END LOOP;
END $$;''')
                
    except Exception as e:
        print(f"Critical error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def main():
    excel_file = "1_insert_data.xlsx"
    output_file = "3_postgresql_inserts.sql"
    schema_file = "2_postgresql_scheme.sql"
    
    try:
        processed_excel = preprocess_excel_file(excel_file, schema_file)
        print(f"Created processed Excel file: {processed_excel}")
        
        generate_insert_statements(processed_excel, output_file, schema_file)
        print(f"Successfully generated INSERT statements in {output_file}")
    except Exception as e:
        print(f"Error occurred: {str(e)}")

if __name__ == "__main__":
    main()
