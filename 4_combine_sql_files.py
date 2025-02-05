import re

def extract_sections(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    def split_sql(sql):
        statements = []
        current = []
        in_string = False
        in_comment = False
        quote_char = None
        
        i = 0
        while i < len(sql):
            char = sql[i]
            
            # Handle comments
            if sql[i:i+2] == '--' and not in_string:
                in_comment = True
                i += 2
                continue
            elif char == '\n' and in_comment:
                in_comment = False
                i += 1
                continue
            elif in_comment:
                i += 1
                continue
                
            # Handle strings
            if char in ["'", '"'] and not in_string:
                in_string = True
                quote_char = char
                current.append(char)
            elif char == quote_char and in_string:
                if sql[max(0, i-1)] != '\\': # Check it's not escaped
                    in_string = False
                    quote_char = None
                current.append(char)
            # Handle statement endings    
            elif char == ';' and not in_string:
                current.append(char)
                stmt = ''.join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
            else:
                current.append(char)
            i += 1
            
        # Add any remaining statement
        stmt = ''.join(current).strip()
        if stmt:
            statements.append(stmt)
            
        return [s for s in statements if s.strip()]

    statements = split_sql(content)
    
    # Improved pattern matching for CREATE TABLE statements
    creates = []
    primary_keys = []
    foreign_keys = []
    inserts = []
    
    for stmt in statements:
        # Handle CREATE TABLE with better pattern matching
        if re.search(r'CREATE\s+TABLE\s+[\w"`]+\s*\(', stmt, re.IGNORECASE):
            creates.append(stmt)
        elif 'ADD PRIMARY KEY' in stmt.upper():
            primary_keys.append(stmt) 
        elif 'ADD FOREIGN KEY' in stmt.upper():
            foreign_keys.append(stmt)
        elif stmt.upper().startswith('INSERT INTO'):
            inserts.append(stmt)
    
    return creates, primary_keys, foreign_keys, inserts

def combine_sql_files(schema_file, insert_file, output_file):
    # Extract sections from schema file
    creates, pks, fks, schema_inserts = extract_sections(schema_file)
    
    # Extract sections from insert file 
    _, _, _, inserts = extract_sections(insert_file)
    
    # Combine all inserts
    all_inserts = schema_inserts + inserts
    
    # Write combined file in desired order
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('-- Combined PostgreSQL Schema and Data\n\n')
        
        # 1. CREATE TABLE statements
        f.write('-- Table Creation\n\n')
        for stmt in creates:
            f.write(stmt + '\n\n')
        
        # 2. Transaction start and disable FK constraints
        f.write('-- Begin transaction\n')
        f.write('BEGIN;\n\n')
        f.write('-- Disable foreign key constraints for all tables\n')
        f.write('SET session_replication_role = \'replica\';\n\n')
        
        # 3. All INSERT statements
        f.write('-- Data Insertion\n\n')
        for stmt in all_inserts:
            f.write(stmt + '\n\n')
        
        # 4. Re-enable FK constraints and commit
        f.write('-- Re-enable foreign key constraints\n')
        f.write('SET session_replication_role = \'origin\';\n\n')
        f.write('-- Commit the transaction\n')
        f.write('COMMIT;\n\n')
            
        # 5. Primary Key constraints
        f.write('-- Primary Keys\n\n')
        for stmt in pks:
            if 'ADD PRIMARY KEY' in stmt:
                f.write(stmt + '\n\n')
        
        # 6. Foreign Key constraints  
        f.write('-- Foreign Keys\n\n')
        for stmt in fks:
            if 'ADD FOREIGN KEY' in stmt:
                f.write(stmt + '\n\n')
                
        # 7. Add sequence reset code at the very end
        f.write('''-- This script generates commands to reset all sequences in the database
-- It will reset sequences based on the maximum value in each table's corresponding column

DO $$
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

if __name__ == '__main__':
    schema_file = "2_postgresql_scheme.sql"
    insert_file = "3_postgresql_inserts.sql"
    output_file = "4_final_postgresql.sql"
    
    try:
        combine_sql_files(schema_file, insert_file, output_file)
        print("Files combined successfully in the correct order!")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
