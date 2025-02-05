import re

def has_id_column(create_statement):
    # Check if the CREATE TABLE statement contains an 'id' column
    return bool(re.search(r'\bid\b.*?(?:integer|bigint|SERIAL)', create_statement, re.IGNORECASE))

def convert_mysql_to_postgresql(input_file, output_file):
    # Read input file
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove MySQL-specific syntax and convert to PostgreSQL
    content = re.sub(r'`', '', content)  # Remove backticks
    content = re.sub(r'ENGINE=.*?;', ';', content)
    content = re.sub(r'AUTO_INCREMENT', 'SERIAL', content, flags=re.IGNORECASE)
    content = re.sub(r'DEFAULT CHARSET=\w+', '', content)
    content = re.sub(r'COLLATE \w+', '', content)
    content = re.sub(r'UNSIGNED', '', content)
    content = re.sub(r'DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP', 'DEFAULT CURRENT_TIMESTAMP', content)
    
    # Convert data types
    type_mappings = {
        r'tinyint\(1\)': 'boolean',
        r'tinyint': 'boolean',
        r'int\(\d+\)': 'integer',
        r'smallint\(\d+\)': 'smallint',
        r'mediumint\(\d+\)': 'integer',
        r'bigint\(\d+\)': 'bigint',
        r'float\(\d+,\d+\)': 'float',
        r'double\(\d+,\d+\)': 'double precision',
        r'datetime': 'timestamp',
        r'varchar': 'character varying',
        r'longtext': 'text',
        r'mediumtext': 'text',
        r'text': 'text',
        r'longblob': 'bytea',
        r'mediumblob': 'bytea',
        r'blob': 'bytea',
        r'enum\([^)]+\)': 'character varying',
        r'decimal': 'numeric'
    }
    
    for mysql_type, pg_type in type_mappings.items():
        content = re.sub(mysql_type, pg_type, content, flags=re.IGNORECASE)
    
    # Extract CREATE TABLE statements only
    create_statements = re.findall(r'CREATE TABLE.*?;', content, re.DOTALL | re.IGNORECASE)

    # Also extract ALTER TABLE statements
    alter_statements = re.findall(r'ALTER TABLE.*?;', content, re.DOTALL | re.IGNORECASE)
    
    # Clean up ALTER statements - remove backticks and CONSTRAINT syntax
    cleaned_alter_statements = []
    for statement in alter_statements:
        # Remove backticks
        cleaned = re.sub(r'`', '', statement)
        # Convert foreign key syntax if needed
        cleaned = re.sub(r'FOREIGN KEY \((.*?)\) REFERENCES (.*?) \((.*?)\)', 
                        r'FOREIGN KEY (\1) REFERENCES \2 (\3)', cleaned)
        # Clean up ON DELETE/UPDATE actions
        cleaned = re.sub(r'ON DELETE CASCADE ON UPDATE CASCADE', 'ON DELETE CASCADE', cleaned)
        cleaned = re.sub(r'ON UPDATE CASCADE', '', cleaned)
        cleaned_alter_statements.append(cleaned)
    
    # First extract table names to generate primary key statements
    primary_key_statements = []
    for create_statement in create_statements:
        table_match = re.search(r'CREATE TABLE (\w+)', create_statement)
        if table_match:
            table = table_match.group(1)
            # Special cases for cache tables
            if table in ['cache', 'cache_locks']:
                primary_key_statements.append(f"ALTER TABLE {table}\n  ADD PRIMARY KEY (key);")
            # Only add PRIMARY KEY for tables with 'id' column
            elif has_id_column(create_statement):
                primary_key_statements.append(f"ALTER TABLE {table}\n  ADD PRIMARY KEY (id);")

    # Extract and clean foreign key relationships
    foreign_key_statements = []
    for statement in alter_statements:
        if 'FOREIGN KEY' in statement:
            # Extract table name
            table_name = re.search(r'ALTER TABLE (\w+)', statement).group(1)
            # Extract foreign key details
            fk_matches = re.findall(r'FOREIGN KEY\s*\(([^)]+)\)\s*REFERENCES\s*(\w+)\s*\(([^)]+)\)', statement)
            for fk_col, ref_table, ref_col in fk_matches:
                foreign_key_statements.append(
                    f"ALTER TABLE {table_name}\n  ADD FOREIGN KEY ({fk_col}) REFERENCES {ref_table}({ref_col});"
                )

    # Write converted schema to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('-- Converted from MySQL to PostgreSQL schema\n\n')
        
        # Write CREATE TABLE statements
        f.write('-- Table Creation\n\n')
        for statement in create_statements:
            # Remove PRIMARY KEY constraints from CREATE TABLE
            cleaned = re.sub(r',\s*PRIMARY KEY\s*\([^)]+\)', '', statement)
            f.write(cleaned + '\n\n')
        
        # Write PRIMARY KEY constraints first
        f.write('\n-- Primary Keys\n\n')
        for statement in primary_key_statements:
            f.write(statement + '\n\n')
        
        # Then write FOREIGN KEY constraints
        f.write('-- Foreign Keys\n\n')
        for statement in foreign_key_statements:
            f.write(statement + '\n\n')

if __name__ == '__main__': 
    input_file = "0_to_be_convert.sql"
    output_file = "2_postgresql_scheme.sql"
    try:
        convert_mysql_to_postgresql(input_file, output_file)
        print("Conversion completed successfully!")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
