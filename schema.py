import sqlite3

class DatabaseSchema:
    def __init__(self, db_name: str = "hospital.db"):
        self.db_name = db_name

    def create_tables(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Users tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'hasta',
                status TEXT NOT NULL DEFAULT 'aktif'
            )
        """)

        # Departments tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # Doctors tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                user_id INTEGER UNIQUE,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (department) REFERENCES departments(name) ON DELETE CASCADE
            )
        """)

        # Appointments tablosu
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                doctor_id INTEGER NOT NULL,
                department TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'aktif',
                FOREIGN KEY (patient_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
                FOREIGN KEY (department) REFERENCES departments(name) ON DELETE CASCADE
            )
        """)

        # Yönetici hesabını oluştur
        cursor.execute("SELECT * FROM users WHERE email = 'admin@admin.com'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (name, email, password, role)
                VALUES ('Admin', 'admin@admin.com', 'admin123', 'yonetici')
            """)

        conn.commit()
        conn.close()

    def drop_tables(self):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS appointments")
        cursor.execute("DROP TABLE IF EXISTS doctors")
        cursor.execute("DROP TABLE IF EXISTS departments")
        cursor.execute("DROP TABLE IF EXISTS users")

        conn.commit()
        conn.close()

    def reset_database(self):
        self.drop_tables()
        self.create_tables() 