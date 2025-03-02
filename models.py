from abc import ABC, abstractmethod
import sqlite3
from typing import List, Optional, Any, Tuple

class DatabaseManager:
    def __init__(self, db_name: str = "hospital.db"):
        self.db_name = db_name
        self.connection = None
        self.connect()

    def connect(self):
        if not self.connection:
            self.connection = sqlite3.connect(self.db_name, check_same_thread=False)

    def get_connection(self) -> sqlite3.Connection:
        self.connect()
        return self.connection

    def execute_query(self, query: str, params: tuple = ()) -> List[Tuple]:
        try:
            cursor = self.get_connection().cursor()
            cursor.execute("PRAGMA foreign_keys = ON")  # Foreign key desteğini aktif et
            cursor.execute(query, params)
            result = cursor.fetchall()
            self.connection.commit()
            return result
        except Exception as e:
            self.connection.rollback()
            raise e

    def get_last_insert_id(self) -> int:
        cursor = self.get_connection().cursor()
        cursor.execute("SELECT last_insert_rowid()")
        return cursor.fetchone()[0]

    def __del__(self):
        if self.connection:
            self.connection.close()

class BaseModel(ABC):
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    @abstractmethod
    def create(self, *args, **kwargs):
        pass

    @abstractmethod
    def update(self, *args, **kwargs):
        pass

    @abstractmethod
    def delete(self, id: int):
        pass

    @abstractmethod
    def get_by_id(self, id: int):
        pass

    @abstractmethod
    def get_all(self):
        pass

class User(BaseModel):
    def create(self, name: str, email: str, password: str, role: str = 'hasta', status: str = 'aktif') -> Optional[int]:
        try:
            query = """INSERT INTO users (name, email, password, role, status)
                      VALUES (?, ?, ?, ?, ?)"""
            self.db.execute_query(query, (name, email, password, role, status))
            return self.db.get_last_insert_id()
        except sqlite3.IntegrityError:
            return None

    def update(self, id: int, **kwargs) -> bool:
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(id)
        
        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
        self.db.execute_query(query, tuple(values))
        return True

    def delete(self, id: int) -> bool:
        # Önce kullanıcının rolünü kontrol et
        user = self.get_by_id(id)
        if user and user[3] == 'doktor':  # user[3] role alanı
            # Doktoru da sil
            query = "DELETE FROM doctors WHERE user_id = ?"
            self.db.execute_query(query, (id,))

        # Sonra kullanıcıyı sil
        query = "DELETE FROM users WHERE id = ?"
        self.db.execute_query(query, (id,))
        return True

    def get_by_id(self, id: int) -> Optional[tuple]:
        query = "SELECT * FROM users WHERE id = ?"
        result = self.db.execute_query(query, (id,))
        return result[0] if result else None

    def get_by_email(self, email: str) -> Optional[tuple]:
        query = "SELECT * FROM users WHERE email = ?"
        result = self.db.execute_query(query, (email,))
        return result[0] if result else None

    def get_all(self) -> List[tuple]:
        query = "SELECT * FROM users"
        return self.db.execute_query(query)

    def authenticate(self, email: str, password: str) -> Optional[tuple]:
        query = "SELECT * FROM users WHERE email = ? AND password = ?"
        result = self.db.execute_query(query, (email, password))
        return result[0] if result else None

class Doctor(BaseModel):
    def create(self, name: str, department: str, user_id: int, start_time: int, end_time: int) -> Optional[int]:
        try:
            query = "INSERT INTO doctors (name, department, user_id, start_time, end_time) VALUES (?, ?, ?, ?, ?)"
            self.db.execute_query(query, (name, department, user_id, start_time, end_time))
            return True
        except sqlite3.IntegrityError:
            return None

    def update(self, id: int, **kwargs) -> bool:
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(id)
        
        query = f"UPDATE doctors SET {', '.join(fields)} WHERE id = ?"
        self.db.execute_query(query, tuple(values))
        return True

    def delete(self, id: int) -> bool:
        # Önce doktorun user_id'sini al
        doctor = self.get_by_id(id)
        if doctor and doctor[3]:  # doctor[3] user_id alanı
            # Kullanıcıyı da sil
            query = "DELETE FROM users WHERE id = ?"
            self.db.execute_query(query, (doctor[3],))

        # Sonra doktoru sil
        query = "DELETE FROM doctors WHERE id = ?"
        self.db.execute_query(query, (id,))
        return True

    def get_by_id(self, id: int) -> Optional[tuple]:
        query = "SELECT * FROM doctors WHERE id = ?"
        result = self.db.execute_query(query, (id,))
        return result[0] if result else None

    def get_all(self) -> List[tuple]:
        query = "SELECT * FROM doctors"
        return self.db.execute_query(query)

    def get_all_with_details(self) -> List[tuple]:
        query = """
            SELECT d.id, d.name, d.department, u.email, d.start_time, d.end_time
            FROM doctors d
            JOIN users u ON d.user_id = u.id
        """
        return self.db.execute_query(query)

    def get_by_department(self, department: str) -> List[tuple]:
        query = "SELECT id, name FROM doctors WHERE department = ?"
        return self.db.execute_query(query, (department,))

    def get_by_user_id(self, user_id: int) -> Optional[tuple]:
        query = "SELECT * FROM doctors WHERE user_id = ?"
        result = self.db.execute_query(query, (user_id,))
        return result[0] if result else None

class Appointment(BaseModel):
    def create(self, patient_id: int, doctor_id: int, department: str, date: str, time: str, status: str = 'aktif') -> bool:
        try:
            query = """INSERT INTO appointments (patient_id, doctor_id, department, date, time, status)
                      VALUES (?, ?, ?, ?, ?, ?)"""
            self.db.execute_query(query, (patient_id, doctor_id, department, date, time, status))
            return True
        except sqlite3.IntegrityError:
            return False

    def update(self, id: int, **kwargs) -> bool:
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(id)
        
        query = f"UPDATE appointments SET {', '.join(fields)} WHERE id = ?"
        self.db.execute_query(query, tuple(values))
        return True

    def delete(self, id: int) -> bool:
        query = "DELETE FROM appointments WHERE id = ?"
        self.db.execute_query(query, (id,))
        return True

    def get_by_id(self, id: int) -> Optional[tuple]:
        query = "SELECT * FROM appointments WHERE id = ?"
        result = self.db.execute_query(query, (id,))
        return result[0] if result else None

    def get_all(self) -> List[tuple]:
        query = """
            SELECT a.*, u.name as patient_name, d.name as doctor_name
            FROM appointments a
            JOIN users u ON a.patient_id = u.id
            JOIN doctors d ON a.doctor_id = d.id
        """
        return self.db.execute_query(query)

    def get_active_appointments(self) -> List[tuple]:
        query = """
            SELECT a.*, u.name as patient_name, d.name as doctor_name
            FROM appointments a
            JOIN users u ON a.patient_id = u.id
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.status = 'aktif'
        """
        return self.db.execute_query(query)

    def get_passive_appointments(self) -> List[tuple]:
        query = """
            SELECT a.*, u.name as patient_name, d.name as doctor_name
            FROM appointments a
            JOIN users u ON a.patient_id = u.id
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.status = 'pasif'
        """
        return self.db.execute_query(query)

    def get_active_appointments_by_patient(self, patient_id: int) -> List[tuple]:
        query = """
            SELECT a.id, a.department, a.date, a.time, a.status, d.name as doctor_name
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.patient_id = ? AND a.status = 'aktif'
        """
        return self.db.execute_query(query, (patient_id,))

    def get_past_appointments_by_patient(self, patient_id: int) -> List[tuple]:
        query = """
            SELECT a.id, a.department, a.date, a.time, a.status, d.name as doctor_name
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.patient_id = ? AND a.status = 'pasif'
        """
        return self.db.execute_query(query, (patient_id,))

    def get_active_appointments_by_doctor(self, doctor_id: int) -> List[tuple]:
        query = """
            SELECT a.id, a.patient_id, u.name as patient_name, a.date, a.time, a.status
            FROM appointments a
            JOIN users u ON a.patient_id = u.id
            WHERE a.doctor_id = ? AND a.status = 'aktif'
        """
        return self.db.execute_query(query, (doctor_id,))

    def get_past_appointments_by_doctor(self, doctor_id: int) -> List[tuple]:
        query = """
            SELECT a.id, a.patient_id, u.name as patient_name, a.date, a.time, a.status
            FROM appointments a
            JOIN users u ON a.patient_id = u.id
            WHERE a.doctor_id = ? AND a.status = 'pasif'
        """
        return self.db.execute_query(query, (doctor_id,))

    def update_expired_appointments(self) -> None:
        query = """
            UPDATE appointments 
            SET status = 'pasif'
            WHERE date < date('now') AND status = 'aktif'
        """
        self.db.execute_query(query, ())

class Department(BaseModel):
    def create(self, name: str) -> bool:
        try:
            query = "INSERT INTO departments (name) VALUES (?)"
            self.db.execute_query(query, (name,))
            return True
        except sqlite3.IntegrityError:
            return False

    def update(self, id: int, **kwargs) -> bool:
        fields = []
        values = []
        for key, value in kwargs.items():
            fields.append(f"{key} = ?")
            values.append(value)
        values.append(id)
        
        query = f"UPDATE departments SET {', '.join(fields)} WHERE id = ?"
        self.db.execute_query(query, tuple(values))
        return True

    def delete(self, id: int) -> bool:
        query = "DELETE FROM departments WHERE id = ?"
        self.db.execute_query(query, (id,))
        return True

    def get_by_id(self, id: int) -> Optional[tuple]:
        query = "SELECT * FROM departments WHERE id = ?"
        result = self.db.execute_query(query, (id,))
        return result[0] if result else None

    def get_all(self) -> List[tuple]:
        query = "SELECT * FROM departments"
        return self.db.execute_query(query) 