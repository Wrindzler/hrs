from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from models import DatabaseManager, User, Doctor, Appointment, Department
from admin import AdminManager
import datetime

class HospitalApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = "your_secret_key"
        
        # Veritabanı ve model nesnelerini oluştur
        self.db_manager = DatabaseManager()
        self.user_model = User(self.db_manager)
        self.doctor_model = Doctor(self.db_manager)
        self.appointment_model = Appointment(self.db_manager)
        self.department_model = Department(self.db_manager)
        
        # Admin yöneticisini oluştur
        self.admin_manager = AdminManager(
            self.user_model,
            self.doctor_model,
            self.department_model,
            self.appointment_model
        )
        
        # Route'ları kaydet
        self.register_routes()

    def register_routes(self):
        # Ana sayfa ve giriş/çıkış route'ları
        self.app.route('/')(self.home)
        self.app.route('/login', methods=['GET', 'POST'])(self.login)
        self.app.route('/register', methods=['GET', 'POST'])(self.register)
        self.app.route('/logout')(self.logout)

        # Dashboard route'ları
        self.app.route('/dashboard/<int:user_id>', methods=['GET', 'POST'])(self.dashboard)
        self.app.route('/doctor/dashboard')(self.doctor_dashboard)
        self.app.route('/admin_dashboard', methods=['GET', 'POST'])(self.admin_dashboard)

        # Admin route'ları
        self.app.route('/admin/appointments')(self.admin_appointments)
        self.app.route('/admin/doctors', methods=['GET', 'POST'])(self.admin_doctors)
        self.app.route('/admin/departments', methods=['GET', 'POST'])(self.admin_departments)
        self.app.route('/admin/users', methods=['GET', 'POST'])(self.admin_users)

        # Randevu işlemleri route'ları
        self.app.route('/book_appointment/<int:user_id>', methods=['GET', 'POST'])(self.book_appointment)
        self.app.route('/get_doctors', methods=['POST'])(self.get_doctors)
        self.app.route('/get_working_hours', methods=['POST'])(self.get_working_hours)
        self.app.route('/cancel_appointment/<int:appointment_id>/<int:user_id>', methods=['POST'])(self.cancel_appointment)
        self.app.route('/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])(self.edit_appointment)
        self.app.route('/edit_appointment_doctor/<int:appointment_id>', methods=['GET', 'POST'])(self.edit_appointment_doctor)
        self.app.route('/edit_appointment_admin/<int:appointment_id>', methods=['GET', 'POST'])(self.edit_appointment_admin)
        self.app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])(self.delete_appointment)

        # Doktor işlemleri route'ları
        self.app.route('/doctor/edit_profile', methods=['GET', 'POST'])(self.edit_doctor_profile)
        self.app.route('/doctor/edit_profile_admin/<int:doctor_id>', methods=['GET', 'POST'])(self.edit_doctor_profile_admin)
        self.app.route('/add_doctor', methods=['GET', 'POST'])(self.add_doctor)
        self.app.route('/delete_doctor/<int:doctor_id>', methods=['POST'])(self.delete_doctor)

        # Bölüm işlemleri route'ları
        self.app.route('/add_department', methods=['GET', 'POST'])(self.add_department)
        self.app.route('/delete_department/<int:department_id>', methods=['POST'])(self.delete_department)

        # Kullanıcı işlemleri route'ları
        self.app.route('/delete_user/<int:user_id>', methods=['POST'])(self.delete_user)
        self.app.route('/toggle_user_status/<int:user_id>', methods=['POST'])(self.toggle_user_status)

        # Her istekten önce çalışacak fonksiyon
        self.app.before_request(self.before_request)

    def home(self):
        return redirect(url_for('login'))

    def login(self):
        # Önceki flash mesajlarını temizle
        session.pop('_flashes', None)
        
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            
            user = self.user_model.get_by_email(email)
            
            if not user:
                flash("Kullanıcı bulunamadı!", "danger")
                return render_template('login.html')
                
            if user[3] != password:  # şifre kontrolü
                flash("Hatalı şifre!", "danger")
                return render_template('login.html')
                
            if user[5] == 'pasif':  # kullanıcı durumu kontrolü
                flash("Hesabınız pasif durumda. Lütfen yönetici ile iletişime geçin.", "danger")
                return render_template('login.html')

            session['logged_in'] = True
            session['user_id'] = user[0]
            
            if user[4] == 'yonetici':  # role kontrolü
                session['is_admin'] = True
                flash("Yönetici olarak giriş yapıldı!", "success")
                return redirect(url_for('admin_dashboard'))
            elif user[4] == 'doktor':
                doctor = self.doctor_model.get_by_user_id(user[0])
                if doctor:
                    session['doctor_id'] = doctor[0]
                    flash("Doktor olarak giriş yapıldı!", "success")
                    return redirect(url_for('doctor_dashboard'))
            else:
                flash("Başarıyla giriş yapıldı!", "success")
                return redirect(url_for('dashboard', user_id=user[0]))

        return render_template('login.html')

    def register(self):
        # Önceki flash mesajlarını temizle
        session.pop('_flashes', None)
        
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            password_confirmation = request.form['password_confirmation']

            if password != password_confirmation:
                flash("Şifreler eşleşmiyor!", "danger")
                return redirect(url_for('register'))

            user_id = self.user_model.create(name, email, password)
            if user_id:
                flash("Kayıt başarılı! Lütfen giriş yapın.", "success")
                return redirect(url_for('login'))
            else:
                flash("Bu e-posta zaten kullanılıyor!", "danger")
        return render_template('register.html')

    def logout(self):
        session.clear()
        flash("Başarıyla çıkış yaptınız!", "success")
        return redirect(url_for('login'))

    def dashboard(self, user_id):
        user = self.user_model.get_by_id(user_id)
        active_appointments = self.appointment_model.get_active_appointments_by_patient(user_id)
        past_appointments = self.appointment_model.get_past_appointments_by_patient(user_id)
        
        return render_template(
            'dashboard.html',
            active_appointments=active_appointments,
            past_appointments=past_appointments,
            user_id=user_id,
            name=user[1] if user else None
        )

    def doctor_dashboard(self):
        doctor_id = session.get('doctor_id')
        if not doctor_id:
            flash("Doktor olarak giriş yapmalısınız!", "danger")
            return redirect(url_for('login'))

        doctor = self.doctor_model.get_by_id(doctor_id)
        active_appointments = self.appointment_model.get_active_appointments_by_doctor(doctor_id)
        passive_appointments = self.appointment_model.get_past_appointments_by_doctor(doctor_id)

        return render_template(
            'doctor_dashboard.html',
            active_appointments=active_appointments,
            passive_appointments=passive_appointments,
            doctor_name=[[doctor[1]]] if doctor else None,
            doctor_department=[[doctor[2]]] if doctor else None
        )

    def admin_dashboard(self):
        dashboard_data = self.admin_manager.get_dashboard_data()
        return render_template('admin_dashboard.html', **dashboard_data)

    def book_appointment(self, user_id):
        if request.method == 'POST':
            department = request.form['department']
            doctor_id = request.form['doctor_id']
            date = request.form['date']
            time = request.form['time']

            success = self.appointment_model.create(user_id, doctor_id, department, date, time)
            if success:
                flash("Randevu başarıyla alındı!", "success")
                return redirect(url_for('dashboard', user_id=user_id))
            else:
                flash("Randevu alınırken bir hata oluştu!", "danger")

        departments = self.department_model.get_all()
        return render_template('book_appointment.html', departments=departments)

    def get_doctors(self):
        department = request.json.get('department')
        doctors = self.doctor_model.get_by_department(department)
        return jsonify([{"id": row[0], "name": "Dr. " + row[1]} for row in doctors])

    def get_working_hours(self):
        doctor_id = request.json.get('doctor_id')
        date = request.json.get('date')
        appointment_id = request.json.get('appointment_id')  # Mevcut randevu ID'si
        
        doctor = self.doctor_model.get_by_id(doctor_id)
        if not doctor:
            return jsonify([])
        
        start_time, end_time = doctor[4], doctor[5]
        booked_appointments = self.appointment_model.get_active_appointments_by_doctor(doctor_id)
        
        # Eğer randevu düzenleme ise, mevcut randevunun saatini booked_times'a ekleme
        booked_times = [int(appt[4].split(':')[0]) for appt in booked_appointments 
                       if appt[3] == date and (not appointment_id or str(appt[0]) != str(appointment_id))]
        
        available_times = []
        for hour in range(start_time, end_time):
            if hour not in booked_times:
                time_str = f"{hour:02d}:00"
                available_times.append(time_str)
        
        return jsonify(available_times)

    def before_request(self):
        self.appointment_model.update_expired_appointments()

    def cancel_appointment(self, appointment_id, user_id):
        if self.appointment_model.delete(appointment_id):
            flash("Randevu başarıyla iptal edildi!", "success")
        else:
            flash("Randevu iptal edilirken bir hata oluştu!", "danger")
        return redirect(url_for('dashboard', user_id=user_id))

    def edit_appointment(self, appointment_id):
        appointment = self.appointment_model.get_by_id(appointment_id)
        if not appointment:
            flash("Randevu bulunamadı!", "danger")
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            department = request.form.get('department')
            doctor_id = request.form.get('doctor_id')
            date = request.form.get('date')
            time = request.form.get('time')

            if self.appointment_model.update(appointment_id, department=department, doctor_id=doctor_id, date=date, time=time):
                flash("Randevu başarıyla güncellendi!", "success")
                return redirect(url_for('dashboard', user_id=appointment[1]))
            else:
                flash("Randevu güncellenirken bir hata oluştu!", "danger")

        departments = self.department_model.get_all()
        doctors = self.doctor_model.get_by_department(appointment[2])
        return render_template('edit_appointment.html', appointment=appointment, departments=departments, doctors=doctors)

    def edit_appointment_doctor(self, appointment_id):
        appointment = self.appointment_model.get_by_id(appointment_id)
        if not appointment:
            flash("Randevu bulunamadı!", "danger")
            return redirect(url_for('doctor_dashboard'))

        if request.method == 'POST':
            department = request.form.get('department')
            doctor_id = request.form.get('doctor_id')
            date = request.form.get('date')
            time = request.form.get('time')

            if self.appointment_model.update(appointment_id, department=department, doctor_id=doctor_id, date=date, time=time):
                flash("Randevu başarıyla güncellendi!", "success")
                return redirect(url_for('doctor_dashboard'))
            else:
                flash("Randevu güncellenirken bir hata oluştu!", "danger")

        departments = self.department_model.get_all()
        doctors = self.doctor_model.get_by_department(appointment[2])
        return render_template('edit_appointment_doctor.html', appointment=appointment, departments=departments, doctors=doctors)

    def edit_appointment_admin(self, appointment_id):
        appointment = self.appointment_model.get_by_id(appointment_id)
        if not appointment:
            flash("Randevu bulunamadı!", "danger")
            return redirect(url_for('admin_dashboard'))

        if request.method == 'POST':
            success, message = self.admin_manager.manage_appointment(appointment_id, request.form)
            flash(message, "success" if success else "danger")
            if success:
                return redirect(url_for('admin_dashboard'))

        departments = self.department_model.get_all()
        doctors = self.doctor_model.get_by_department(appointment[2])
        return render_template('edit_appointment_admin.html', 
                             appointment=appointment,
                             departments=departments,
                             doctors=doctors)

    def delete_appointment(self, appointment_id):
        if self.appointment_model.delete(appointment_id):
            flash("Randevu başarıyla silindi!", "success")
        else:
            flash("Randevu silinirken bir hata oluştu!", "danger")

        # Kullanıcı rolüne göre yönlendirme yap
        if session.get('doctor_id'):
            return redirect(url_for('doctor_dashboard'))
        elif session.get('is_admin'):
            return redirect(url_for('admin_appointments'))
        else:
            return redirect(url_for('dashboard', user_id=session.get('user_id')))

    def edit_doctor_profile(self):
        doctor_id = session.get('doctor_id')
        if not doctor_id:
            flash("Giriş yapmanız gerekiyor!", "danger")
            return redirect(url_for('login'))

        doctor = self.doctor_model.get_by_id(doctor_id)
        if request.method == 'POST':
            department = request.form.get('department')
            start_time = request.form.get('start_time').split(':')[0]  # "09:00" -> "09"
            end_time = request.form.get('end_time').split(':')[0]  # "17:00" -> "17"

            if self.doctor_model.update(doctor_id, department=department, start_time=start_time, end_time=end_time):
                flash("Profil başarıyla güncellendi!", "success")
                return redirect(url_for('doctor_dashboard'))
            else:
                flash("Profil güncellenirken bir hata oluştu!", "danger")

        departments = self.department_model.get_all()
        # Doktorun mevcut departmanını, başlangıç ve bitiş saatlerini al
        doctor_department = self.doctor_model.get_by_id(doctor_id)
        doctor_start_time = [[str(doctor[4])]] if doctor else None
        doctor_end_time = [[str(doctor[5])]] if doctor else None

        return render_template('edit_doctor_profile.html', 
                            doctor=doctor, 
                            departments=departments,
                            doctor_department=[[doctor[2]]] if doctor else None,
                            doctor_start_time=doctor_start_time,
                            doctor_end_time=doctor_end_time)

    def edit_doctor_profile_admin(self, doctor_id):
        if not session.get('is_admin'):
            flash("Bu sayfaya erişim yetkiniz yok!", "danger")
            return redirect(url_for('login'))

        doctor = self.doctor_model.get_by_id(doctor_id)
        if not doctor:
            flash("Doktor bulunamadı!", "danger")
            return redirect(url_for('admin_doctors'))

        if request.method == 'POST':
            department = request.form.get('department')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')

            if not all([department, start_time, end_time]):
                flash("Tüm alanları doldurmak zorunludur!", "danger")
                return redirect(url_for('edit_doctor_profile_admin', doctor_id=doctor_id))

            # Saat değerlerini ayır
            try:
                start_time = start_time.split(':')[0]  # "09:00" -> "09"
                end_time = end_time.split(':')[0]  # "17:00" -> "17"
            except (AttributeError, IndexError):
                flash("Geçersiz saat formatı!", "danger")
                return redirect(url_for('edit_doctor_profile_admin', doctor_id=doctor_id))

            if self.doctor_model.update(doctor_id, department=department, start_time=start_time, end_time=end_time):
                flash("Profil başarıyla güncellendi!", "success")
                return redirect(url_for('admin_doctors'))
            else:
                flash("Profil güncellenirken bir hata oluştu!", "danger")

        departments = self.department_model.get_all()
        # Doktorun mevcut departmanını, başlangıç ve bitiş saatlerini al
        doctor_start_time = [[str(doctor[4])]] if doctor else None
        doctor_end_time = [[str(doctor[5])]] if doctor else None

        return render_template('edit_doctor_profile_admin.html', 
                            doctor=doctor, 
                            departments=departments,
                            doctor_department=[[doctor[2]]] if doctor else None,
                            doctor_start_time=doctor_start_time,
                            doctor_end_time=doctor_end_time)

    def add_doctor(self):
        if not session.get('is_admin'):
            flash("Bu sayfaya erişim yetkiniz yok!", "danger")
            return redirect(url_for('login'))

        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            password = request.form.get('password')
            department = request.form.get('department')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')

            if not all([name, email, password, department, start_time, end_time]):
                flash("Tüm alanları doldurmak zorunludur!", "danger")
                return redirect(url_for('admin_doctors'))

            # Önce kullanıcıyı oluştur
            user_id = self.user_model.create(name, email, password, role='doktor')
            if not user_id:
                flash("Bu e-posta adresi zaten kullanımda!", "danger")
                return redirect(url_for('admin_doctors'))

            # Sonra doktoru oluştur
            if self.doctor_model.create(name, department, user_id, int(start_time), int(end_time)):
                flash("Doktor başarıyla eklendi!", "success")
            else:
                # Doktor oluşturulamazsa kullanıcıyı da sil
                self.user_model.delete(user_id)
                flash("Doktor eklenirken bir hata oluştu!", "danger")

            return redirect(url_for('admin_doctors'))

        departments = self.department_model.get_all()
        doctors = self.doctor_model.get_all()
        return render_template('admin_doctors.html', doctors=doctors, departments=departments)

    def delete_doctor(self, doctor_id):
        success, message = self.admin_manager.delete_doctor(doctor_id)
        flash(message, "success" if success else "danger")
        return redirect(url_for('admin_doctors'))

    def admin_doctors(self):
        doctors = self.doctor_model.get_all_with_details()
        departments = self.department_model.get_all()
        return render_template('admin_doctors.html', doctors=doctors, departments=departments)

    def add_department(self):
        if request.method == 'POST':
            name = request.form['name']
            success, message = self.admin_manager.manage_department(name=name)
            flash(message, "success" if success else "danger")
            return redirect(url_for('admin_dashboard'))
        return render_template('add_department.html')

    def delete_department(self, department_id):
        success, message = self.admin_manager.manage_department(department_id=department_id, action='delete')
        flash(message, "success" if success else "danger")
        return redirect(url_for('admin_departments'))

    def admin_departments(self):
        departments = self.department_model.get_all()
        return render_template('admin_departments.html', departments=departments)

    def admin_users(self):
        users = self.user_model.get_all()
        return render_template('admin_users.html', users=users)

    def delete_user(self, user_id):
        success, message = self.admin_manager.manage_user(user_id, 'delete')
        flash(message, "success" if success else "danger")
        return redirect(url_for('admin_users'))

    def toggle_user_status(self, user_id):
        success, message = self.admin_manager.manage_user(user_id, 'toggle_status')
        flash(message, "success" if success else "danger")
        return redirect(url_for('admin_users'))

    def admin_appointments(self):
        active_appointments = self.appointment_model.get_active_appointments()
        passive_appointments = self.appointment_model.get_passive_appointments()

        return render_template(
            'admin_appointments.html',
            active_appointments=active_appointments,
            passive_appointments=passive_appointments
        )

    def run(self, debug=True):
        self.app.run(debug=debug)

if __name__ == '__main__':
    app = HospitalApp()
    app.run(debug=True) 