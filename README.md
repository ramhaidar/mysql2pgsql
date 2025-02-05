# MySQL to PostgreSQL Migration Tool

A robust Python-based utility for converting MySQL database dumps to PostgreSQL-compatible format. This tool handles various syntax differences, data type conversions, and ensures proper migration of your database structure and content.

## Features

-   Automated conversion of MySQL dump files to PostgreSQL format
-   Smart data type mapping (e.g., `INT(11)` → `INTEGER`, `TINYINT(1)` → `BOOLEAN`)
-   Handles MySQL-specific syntax (`AUTO_INCREMENT`, `ENGINE=InnoDB`)
-   Proper formatting of `INSERT` statements for PostgreSQL
-   Automatic sequence reset after data import
-   Transaction-safe data import process

## Prerequisites

-   Python 3.7 or higher
-   Required Python packages:
    ```
    pandas
    sqlparse
    openpyxl
    xlsxwriter
    ```

## Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/ramhaidar/mysql2pgsql.git
    cd mysql2pgsql
    ```

2. Install dependencies:
    ```bash
    pip install pandas sqlparse openpyxl xlsxwriter
    ```

## Usage

1. Place your MySQL dump file in the project directory as `0_to_be_convert.sql`

2. Run the conversion process in sequence:

    ```bash
    # Step 1: Convert SQL INSERT statements to Excel format
    python 1_convert_to_xlsx.py

    # Step 2: Convert MySQL schema to PostgreSQL format
    python 2_convert_to_pgsql_scheme.py

    # Step 3: Generate PostgreSQL INSERT statements
    python 3_convert_to_pgsql_insert.py

    # Step 4: Combine schema and data into final SQL file
    python 4_combine_sql_files.py
    ```

3. The final PostgreSQL-compatible SQL file will be generated as `4_final_postgresql.sql`

## Output Files

-   `1_insert_data.xlsx`: Intermediate Excel file containing extracted data
-   `2_postgresql_scheme.sql`: Converted PostgreSQL schema
-   `3_processed_insert_data.xlsx`: Processed Excel file with corrected data types and boolean values
-   `3_postgresql_inserts.sql`: Converted PostgreSQL INSERT statements
-   `4_final_postgresql.sql`: Final combined SQL file ready for import

## Important Notes

-   Always backup your database before performing any migration
-   Review the generated SQL file before executing it
-   Large datasets may require additional memory resources
-   Some complex MySQL features might need manual review

## Contributing

We welcome contributions! Please feel free to:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or have suggestions:

1. Check existing issues or create a new one
2. Provide detailed information about the problem
3. Include relevant error messages and logs

## Acknowledgments

Thanks to all contributors who have helped improve this tool.

---

For additional information or questions, please open an issue in the repository.
