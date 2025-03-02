from models import User, Doctor, Department, Appointment
from flask import flash, redirect, url_for, render_template, request

class AdminManager:
    def __init__(self, user_model: User, doctor_model: Doctor, 
                 department_model: Department, appointment_model: Appointment):
        self.user_model = user_model
        self.doctor_model = doctor_model
        self.department_model = department_model
        self.appointment_model = appointment_model

    def get_dashboard_data(self):
        """Admin paneli için tüm verileri getirir"""
        return {
            'appointments': self.appointment_model.get_all(),
            'doctors': self.doctor_model.get_all(),
            'departments': self.department_model.get_all(),
            'users': self.user_model.get_all()
        }

    def manage_doctor(self, request_form=None, doctor_id=None):
        """Doktor ekleme, güncelleme ve silme işlemleri"""
        if request_form:
            name = request_form['name']
            email = request_form['email']
            password = request_form['password']
            department = request_form['department']
            start_time = request_form['start_time']
            end_time = request_form['end_time']

            if doctor_id:  # Güncelleme
                doctor = self.doctor_model.get_by_id(doctor_id)
                if doctor:
                    self.doctor_model.update(doctor_id, 
                                          department=department,
                                          start_time=start_time,
                                          end_time=end_time)
                    return True, "Doktor başarıyla güncellendi!"
                return False, "Doktor bulunamadı!"
            else:  # Yeni doktor ekleme
                user_id = self.user_model.create(name, email, password, role='doktor')
                if user_id:
                    if self.doctor_model.create(name, department, user_id, int(start_time), int(end_time)):
                        return True, "Doktor başarıyla eklendi!"
                    else:
                        self.user_model.delete(user_id)
                        return False, "Doktor eklenirken bir hata oluştu!"
                return False, "Bu e-posta zaten kullanılıyor!"
        
        return True, None

    def delete_doctor(self, doctor_id: int):
        """Doktor silme işlemi"""
        doctor = self.doctor_model.get_by_id(doctor_id)
        if doctor and doctor[3]:  # user_id kontrolü
            self.user_model.delete(doctor[3])
        
        if self.doctor_model.delete(doctor_id):
            return True, "Doktor başarıyla silindi!"
        return False, "Doktor silinirken bir hata oluştu!"

    def manage_department(self, name=None, department_id=None, action='add'):
        """Bölüm ekleme, güncelleme ve silme işlemleri"""
        if action == 'add' and name:
            if self.department_model.create(name):
                return True, "Bölüm başarıyla eklendi!"
            return False, "Bölüm eklenirken bir hata oluştu!"
        
        elif action == 'delete' and department_id:
            if self.department_model.delete(department_id):
                return True, "Bölüm başarıyla silindi!"
            return False, "Bölüm silinirken bir hata oluştu!"
        
        elif action == 'update' and department_id and name:
            if self.department_model.update(department_id, name=name):
                return True, "Bölüm başarıyla güncellendi!"
            return False, "Bölüm güncellenirken bir hata oluştu!"

        return False, "Geçersiz işlem!"

    def manage_user(self, user_id: int, action: str):
        """Kullanıcı yönetimi işlemleri"""
        if action == 'delete':
            if self.user_model.delete(user_id):
                return True, "Kullanıcı başarıyla silindi!"
            return False, "Kullanıcı silinirken bir hata oluştu!"
        
        elif action == 'toggle_status':
            user = self.user_model.get_by_id(user_id)
            if user:
                new_status = 'aktif' if user[5] == 'pasif' else 'pasif'
                if self.user_model.update(user_id, status=new_status):
                    return True, f"Kullanıcı durumu '{new_status}' olarak güncellendi!"
                return False, "Kullanıcı durumu güncellenirken bir hata oluştu!"
            return False, "Kullanıcı bulunamadı!"

        return False, "Geçersiz işlem!"

    def manage_appointment(self, appointment_id: int, form_data=None):
        """Randevu yönetimi işlemleri"""
        if form_data:
            department = form_data.get('department')
            doctor_id = form_data.get('doctor_id')
            date = form_data.get('date')
            time = form_data.get('time')

            if self.appointment_model.update(appointment_id, 
                                          department=department,
                                          doctor_id=doctor_id,
                                          date=date,
                                          time=time):
                return True, "Randevu başarıyla güncellendi!"
            return False, "Randevu güncellenirken bir hata oluştu!"
        
        elif appointment_id:
            if self.appointment_model.delete(appointment_id):
                return True, "Randevu başarıyla silindi!"
            return False, "Randevu silinirken bir hata oluştu!"

        return False, "Geçersiz işlem!" 