# mysql2pgsql

This repository contains a Python script for automatically converting **MySQL** dump files to **PostgreSQL**. The script helps handle syntax differences between the two databases, including data type conversions, index formatting, and other necessary adjustments.

### **🚀 Key Features:**

✔ Automatically converts MySQL dump files to PostgreSQL-compatible SQL  
✔ Adjusts common data types (e.g., `INT(11) -> INTEGER`, `TINYINT(1) -> BOOLEAN`)  
✔ Transforms MySQL-specific syntax such as `AUTO_INCREMENT`, `ENGINE=InnoDB` for PostgreSQL compatibility  
✔ Modifies `INSERT` statements to match PostgreSQL format

### **⚠ Note:**

This is a personal project and still a work in progress, so it may not be perfect, and bugs might exist. If you encounter any issues or have suggestions for improvements, feel free to open an issue or submit a pull request. Contributions in any form—feedback, ideas, or code improvements—are highly appreciated! 😊

### **📌 Roadmap (Upcoming Features):**

🔹 Performance optimization for large dump files  
🔹 Expanded data type conversion support  
🔹 Automatic handling of constraints and foreign keys

---

### **🔗 How to Contribute:**

1. Fork this repository
2. Create a new branch (`feature-your_feature_name`)
3. Commit your changes
4. Submit a pull request 🎉

Thanks for stopping by! 🚀
