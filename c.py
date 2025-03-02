from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import datetime
from flask import jsonify

app = Flask(__name__)
app.secret_key = "your_secret_key"

conn = sqlite3.connect("hospital.db")
cursor = conn.cursor()
cursor.execute("UPDATE appointments SET status='pasif' WHERE id=30 ")
bolumler=cursor.execute("SELECT * FROM departments").fetchall()
kullanicilar=cursor.execute("SELECT * FROM users").fetchall()
doktorlar=cursor.execute("SELECT * FROM doctors").fetchall()
randevular=cursor.execute("SELECT * FROM appointments").fetchall()
tablo=[bolumler,kullanicilar,doktorlar,randevular]
conn.commit()
conn.close()

for i in tablo:
    for j in i:
        print(j)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect("hospital.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['email'] = email
            session['role'] = user[4]  # Kullanıcının rolünü session'a kaydediyoruz
            if user[4] == 'hasta':
                return redirect(url_for('dashboard', user_id=user[0]))
            elif user[4] == 'doktor':
                # Doktor ID'sini almak için ek bir sorgu
                conn = sqlite3.connect("hospital.db")
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM doctors WHERE user_id = ?", (user[0],))
                doctor = cursor.fetchone()
                conn.close()

                if doctor:
                    session['doctor_id'] = doctor[0]  # Doktor ID'sini session'a kaydediyoruz
                    return redirect(url_for('doctor_dashboard'))
                else:
                    flash("Doktor bilgileri bulunamadı!", "danger")
            elif user[4] == 'yonetici':
                return redirect(url_for('admin_dashboard'))
        else:
            flash("Geçersiz e-posta veya şifre!", "danger")
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        password_confirmation = request.form['password_confirmation']

        if password != password_confirmation:
            flash("Şifreler eşleşmiyor!", "danger")
            return redirect(url_for('register'))

        conn = sqlite3.connect("hospital.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", 
                           (name, email, password, 'hasta'))
            conn.commit()
            flash("Kayıt başarılı! Lütfen giriş yapın.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Bu e-posta zaten kullanılıyor!", "danger")
        conn.close()
    return render_template('register.html')

@app.route('/dashboard/<int:user_id>', methods=['GET', 'POST'])
def dashboard(user_id):

    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM users WHERE id=?",(user_id,))
    name=cursor.fetchall()

    cursor.execute("""
        SELECT a.id, a.department, a.date, a.time, a.status, d.name as doctor_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.patient_id = ? AND a.status = 'aktif'
    """, (user_id,))
    active_appointments = cursor.fetchall()

    cursor.execute("""
        SELECT a.id, a.department, a.date, a.time, a.status, d.name as doctor_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.patient_id = ? AND (a.status = 'pasif')
    """, (user_id,))
    past_appointments = cursor.fetchall()

    conn.close()
    return render_template(
        'dashboard.html',
        active_appointments=active_appointments,
        past_appointments=past_appointments,
        user_id=user_id,
        name=name
    )

# Add this new route to your Flask application
@app.route('/get_working_hours', methods=['POST'])
def get_working_hours():
    doctor_id = request.json.get('doctor_id')
    date = request.json.get('date')
    
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    
    # Get doctor's working hours
    cursor.execute("SELECT start_time, end_time FROM doctors WHERE id = ?", (doctor_id,))
    working_hours = cursor.fetchone()
    
    if not working_hours:
        conn.close()
        return jsonify([])
    
    start_time, end_time = working_hours
    
    # Get existing appointments for the doctor on the selected date
    cursor.execute("""
        SELECT time 
        FROM appointments 
        WHERE doctor_id = ? AND date = ? AND status = 'aktif'
    """, (doctor_id, date))
    
    booked_times = [int(row[0].split(':')[0]) for row in cursor.fetchall()]
    
    # Generate available time slots
    available_times = []
    for hour in range(start_time, end_time):
        if hour not in booked_times:
            time_str = f"{hour:02d}:00"
            available_times.append(time_str)
    
    conn.close()
    return jsonify(available_times)

# Update your book_appointment route to handle the time validation
@app.route('/book_appointment/<int:user_id>', methods=['GET', 'POST'])
def book_appointment(user_id):
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    if request.method == 'POST':
        department = request.form['department']
        doctor_id = request.form['doctor_id']
        date = request.form['date']
        time = request.form['time']

        # Check if the time slot is already booked
        cursor.execute("""
            SELECT COUNT(*) 
            FROM appointments 
            WHERE doctor_id = ? AND date = ? AND time = ? AND status = 'aktif'
        """, (doctor_id, date, time))
        
        if cursor.fetchone()[0] > 0:
            flash("Bu randevu saati dolu!", "danger")
            conn.close()
            return redirect(url_for('book_appointment', user_id=user_id))

        # Get doctor's working hours
        cursor.execute("SELECT start_time, end_time FROM doctors WHERE id = ?", (doctor_id,))
        doctor = cursor.fetchone()

        if doctor:
            start_time, end_time = doctor
            appointment_hour = int(time.split(':')[0])
            
            if not (start_time <= appointment_hour < end_time):
                flash(f"Randevu saati, doktorun çalışma saatleri arasında olmalıdır: {start_time}:00 - {end_time}:00", "danger")
                conn.close()
                return redirect(url_for('book_appointment', user_id=user_id))

            cursor.execute(
                '''INSERT INTO appointments (patient_id, doctor_id, department, date, time, status)
                   VALUES (?, ?, ?, ?, ?, ?)''', (user_id, doctor_id, department, date, time, 'aktif'))
            conn.commit()
            flash("Randevu başarıyla alındı!", "success")
            return redirect(url_for('dashboard', user_id=user_id))

    conn.close()
    return render_template('book_appointment.html', departments=departments)

@app.route('/get_doctors', methods=['POST'])
def get_doctors():
    department = request.json.get('department')
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM doctors WHERE department = ?", (department,))
    doctors = [{"id": row[0], "name": "Dr. " + row[1]} for row in cursor.fetchall()]

    conn.close()
    return jsonify(doctors)

@app.route('/cancel_appointment/<int:appointment_id>/<int:user_id>', methods=['POST'])
def cancel_appointment(appointment_id, user_id):
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()
    flash("Randevu başarıyla iptal edildi!", "success")
    return redirect(url_for('dashboard', user_id=user_id))

@app.route('/logout')
def logout():
    session.clear()  # Tüm oturum verilerini temizler
    flash("Başarıyla çıkış yaptınız!", "success")
    return redirect(url_for('login'))

@app.route('/doctor/dashboard')
def doctor_dashboard():
    doctor_id = session.get('doctor_id')
    if not doctor_id:
        flash("Doktor olarak giriş yapmalısınız!", "danger")
        return redirect(url_for('login'))

    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    # Randevu sorguları
    cursor.execute("""
        SELECT a.id, a.patient_id, u.name as patient_name, a.date, a.time, a.status
        FROM appointments a
        JOIN users u ON a.patient_id = u.id
        WHERE a.doctor_id = ? AND a.status = 'aktif'
    """, (doctor_id,))
    active_appointments = cursor.fetchall()

    cursor.execute("""
        SELECT a.id, a.patient_id, u.name as patient_name, a.date, a.time, a.status
        FROM appointments a
        JOIN users u ON a.patient_id = u.id
        WHERE a.doctor_id = ? AND a.status = 'pasif'
    """, (doctor_id,))
    passive_appointments = cursor.fetchall()

    cursor.execute("SELECT name FROM doctors WHERE id=?",(doctor_id,))
    doctor_name=cursor.fetchall()

    cursor.execute("SELECT department FROM doctors WHERE id=?",(doctor_id,))
    doctor_department=cursor.fetchall()

    conn.close()

    return render_template(
        'doctor_dashboard.html',
        active_appointments=active_appointments,
        passive_appointments=passive_appointments,
        doctor_name=doctor_name,
        doctor_department=doctor_department
    )

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():

    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM appointments")
    appointments = cursor.fetchall()

    cursor.execute("SELECT * FROM doctors")
    doctors = cursor.fetchall()

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()
    
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    conn.close()
    return render_template(
        'admin_dashboard.html',
        appointments=appointments,
        doctors=doctors,
        departments=departments,
        users=users
    )


@app.route('/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        department_id = request.form['department']
        start_time = request.form['start_time']
        end_time = request.form['end_time']

        try:
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                           (name, email, password, 'doktor'))
            user_id = cursor.lastrowid

            cursor.execute("INSERT INTO doctors (name, department, user_id, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
                           (name, department_id, user_id, start_time, end_time))

            conn.commit()
            flash("Doktor başarıyla eklendi!", "success")
            return redirect(url_for('admin_doctors'))
        except sqlite3.IntegrityError:
            flash("Bu e-posta zaten kullanılıyor!", "danger")
        finally:
            conn.close()

    return render_template('admin_doctors.html', departments=departments)

@app.route('/add_department', methods=['GET', 'POST'])
def add_department():
    if request.method == 'POST':
        name = request.form['name']
        conn = sqlite3.connect("hospital.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO departments (name) VALUES (?)", (name,))
        conn.commit()
        conn.close()
        flash("Bölüm başarıyla eklendi!", "success")
        return redirect(url_for('admin_dashboard'))
    return render_template('add_department.html')

@app.route('/delete_appointment/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()
    flash("Randevu başarıyla silindi!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_doctor/<int:doctor_id>', methods=['POST'])
def delete_doctor(doctor_id):
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM doctors WHERE id = ?", (doctor_id,))
    id=cursor.fetchall()
    id=int(str(id[0])[1:-2])
    cursor.execute("DELETE FROM users WHERE id = ?", (id,))
    cursor.execute("DELETE FROM doctors WHERE id = ?", (doctor_id,))
    conn.commit()
    conn.close()
    flash("Doktor başarıyla silindi!", "success")
    return redirect(url_for('admin_doctors'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        role = user[0]
        if role == "doktor":
            cursor.execute("DELETE FROM doctors WHERE user_id = ?", (user_id,))
        
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        flash("Kullanıcı başarıyla silindi!", "success")
    else:
        flash("Kullanıcı bulunamadı!", "danger")
    
    conn.close()
    return redirect(url_for('admin_users'))


@app.route('/delete_department/<int:department_id>', methods=['POST'])
def delete_department(department_id):
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM doctors WHERE department = ?", (department_id,))
        doctor_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM appointments WHERE department = ?", (department_id,))
        appointment_count = cursor.fetchone()[0]

        if doctor_count > 0 or appointment_count > 0:
            flash("Bu bölümle ilişkili doktorlar veya randevular olduğu için silinemez.", "danger")
        else:
            cursor.execute("DELETE FROM departments WHERE id = ?", (department_id,))
            conn.commit()
            flash("Bölüm başarıyla silindi!", "success")
    except Exception as e:
        flash(f"Bir hata oluştu: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for('admin_departments'))

@app.route('/edit_appointment/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment(appointment_id):
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    # Get current appointment details
    cursor.execute("""
        SELECT a.*, d.name as doctor_name 
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.id = ?
    """, (appointment_id,))
    appointment = cursor.fetchone()

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    if request.method == 'POST':
        department = request.form.get('department')
        doctor_id = request.form.get('doctor_id')
        date = request.form.get('date')
        time = request.form.get('time')

        if not all([department, doctor_id, date, time]):
            flash("Tüm alanları doldurmanız gerekmektedir!", "danger")
            return redirect(url_for('edit_appointment', appointment_id=appointment_id))

        # Check if the time slot is already booked (excluding current appointment)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM appointments 
            WHERE doctor_id = ? AND date = ? AND time = ? AND id != ? AND status = 'aktif'
        """, (doctor_id, date, time, appointment_id))
        
        if cursor.fetchone()[0] > 0:
            flash("Bu randevu saati dolu!", "danger")
            return redirect(url_for('edit_appointment', appointment_id=appointment_id))

        # Check doctor's working hours
        cursor.execute("SELECT start_time, end_time FROM doctors WHERE id = ?", (doctor_id,))
        doctor = cursor.fetchone()

        if doctor:
            start_time, end_time = doctor
            appointment_hour = int(time.split(':')[0])
            
            if not (start_time <= appointment_hour < end_time):
                flash(f"Randevu saati, doktorun çalışma saatleri arasında olmalıdır: {start_time}:00 - {end_time}:00", "danger")
                return redirect(url_for('edit_appointment', appointment_id=appointment_id))

            cursor.execute("""
                UPDATE appointments 
                SET department = ?, doctor_id = ?, date = ?, time = ?
                WHERE id = ?
            """, (department, doctor_id, date, time, appointment_id))
            
            conn.commit()
            flash("Randevu başarıyla güncellendi!", "success")
            return redirect(url_for('dashboard'))

    # Get doctors for the current department
    cursor.execute("SELECT id, name FROM doctors WHERE department = ?", (appointment[2],))
    doctors = cursor.fetchall()

    conn.close()
    return render_template('edit_appointment.html', 
                         appointment=appointment, 
                         departments=departments, 
                         doctors=doctors)

@app.route('/edit_appointment_doctor/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment_doctor(appointment_id):
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    # Get current appointment details
    cursor.execute("""
        SELECT a.*, d.name as doctor_name 
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.id = ?
    """, (appointment_id,))
    appointment = cursor.fetchone()

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    if request.method == 'POST':
        department = request.form.get('department')
        doctor_id = request.form.get('doctor_id')
        date = request.form.get('date')
        time = request.form.get('time')

        if not all([department, doctor_id, date, time]):
            flash("Tüm alanları doldurmanız gerekmektedir!", "danger")
            return redirect(url_for('edit_appointment', appointment_id=appointment_id))

        # Check if the time slot is already booked (excluding current appointment)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM appointments 
            WHERE doctor_id = ? AND date = ? AND time = ? AND id != ? AND status = 'aktif'
        """, (doctor_id, date, time, appointment_id))
        
        if cursor.fetchone()[0] > 0:
            flash("Bu randevu saati dolu!", "danger")
            return redirect(url_for('edit_appointment_doctor', appointment_id=appointment_id))

        # Check doctor's working hours
        cursor.execute("SELECT start_time, end_time FROM doctors WHERE id = ?", (doctor_id,))
        doctor = cursor.fetchone()

        if doctor:
            start_time, end_time = doctor
            appointment_hour = int(time.split(':')[0])
            
            if not (start_time <= appointment_hour < end_time):
                flash(f"Randevu saati, doktorun çalışma saatleri arasında olmalıdır: {start_time}:00 - {end_time}:00", "danger")
                return redirect(url_for('edit_appointment_doctor', appointment_id=appointment_id))

            cursor.execute("""
                UPDATE appointments 
                SET department = ?, doctor_id = ?, date = ?, time = ?
                WHERE id = ?
            """, (department, doctor_id, date, time, appointment_id))
            
            conn.commit()
            flash("Randevu başarıyla güncellendi!", "success")
            return redirect(url_for('doctor_dashboard'))

    # Get doctors for the current department
    cursor.execute("SELECT id, name FROM doctors WHERE department = ?", (appointment[2],))
    doctors = cursor.fetchall()

    conn.close()
    return render_template('edit_appointment.html', 
                         appointment=appointment, 
                         departments=departments, 
                         doctors=doctors)

@app.route('/edit_appointment_admin/<int:appointment_id>', methods=['GET', 'POST'])
def edit_appointment_admin(appointment_id):
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    # Get current appointment details
    cursor.execute("""
        SELECT a.*, d.name as doctor_name 
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.id
        WHERE a.id = ?
    """, (appointment_id,))
    appointment = cursor.fetchone()

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()

    if request.method == 'POST':
        department = request.form.get('department')
        doctor_id = request.form.get('doctor_id')
        date = request.form.get('date')
        time = request.form.get('time')

        if not all([department, doctor_id, date, time]):
            flash("Tüm alanları doldurmanız gerekmektedir!", "danger")
            return redirect(url_for('edit_appointment_admin', appointment_id=appointment_id))

        # Check if the time slot is already booked (excluding current appointment)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM appointments 
            WHERE doctor_id = ? AND date = ? AND time = ? AND id != ? AND status = 'aktif'
        """, (doctor_id, date, time, appointment_id))
        
        if cursor.fetchone()[0] > 0:
            flash("Bu randevu saati dolu!", "danger")
            return redirect(url_for('edit_appointment_admin', appointment_id=appointment_id))

        # Check doctor's working hours
        cursor.execute("SELECT start_time, end_time FROM doctors WHERE id = ?", (doctor_id,))
        doctor = cursor.fetchone()

        if doctor:
            start_time, end_time = doctor
            appointment_hour = int(time.split(':')[0])
            
            if not (start_time <= appointment_hour < end_time):
                flash(f"Randevu saati, doktorun çalışma saatleri arasında olmalıdır: {start_time}:00 - {end_time}:00", "danger")
                return redirect(url_for('edit_appointment_doctor', appointment_id=appointment_id))

            cursor.execute("""
                UPDATE appointments 
                SET department = ?, doctor_id = ?, date = ?, time = ?
                WHERE id = ?
            """, (department, doctor_id, date, time, appointment_id))
            
            conn.commit()
            flash("Randevu başarıyla güncellendi!", "success")
            return redirect(url_for('admin_dashboard'))

    # Get doctors for the current department
    cursor.execute("SELECT id, name FROM doctors WHERE department = ?", (appointment[2],))
    doctors = cursor.fetchall()

    conn.close()
    return render_template('edit_appointment.html', 
                         appointment=appointment, 
                         departments=departments, 
                         doctors=doctors)

@app.route('/doctor/edit_profile', methods=['GET', 'POST'])
def edit_doctor_profile():
    user_id = session.get('doctor_id')
    if not user_id:
        flash("Giriş yapmanız gerekiyor!", "danger")
        return redirect(url_for('login'))

    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.id, d.name, d.department, d.start_time, d.end_time
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        WHERE u.id = ?
    """, (user_id,))
    doctor = cursor.fetchone()
    print(doctor)

    cursor.execute("SELECT id, name FROM departments")
    departments = cursor.fetchall()

    cursor.execute("SELECT department FROM doctors WHERE id=?",(user_id,))
    doctor_department=cursor.fetchall()

    cursor.execute("SELECT start_time FROM doctors WHERE id=?",(user_id,))
    doctor_start_time=cursor.fetchall()

    cursor.execute("SELECT end_time FROM doctors WHERE id=?",(user_id,))
    doctor_end_time=cursor.fetchall()

    if request.method == 'POST':
        department = request.form.get('department')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        if not (start_time and end_time):
            flash("Çalışma saatlerini belirtmeniz gerekiyor!", "danger")
        elif start_time >= end_time:
            flash("Başlangıç saati, bitiş saatinden önce olmalıdır!", "danger")
        else:
            cursor.execute("""
                UPDATE doctors
                SET department = ?, start_time = ?, end_time = ?
                WHERE id = ?
            """, (department, start_time, end_time, user_id))
            conn.commit()
            flash("Profil başarıyla güncellendi!", "success")
            conn.close()
            return redirect(url_for('doctor_dashboard'))

    conn.close()
    return render_template('edit_doctor_profile.html', doctor=doctor, departments=departments, doctor_department=doctor_department,
                           doctor_start_time=doctor_start_time,doctor_end_time=doctor_end_time)


@app.route('/doctor/edit_profile_admin', methods=['GET', 'POST'])
def edit_doctor_profile_admin():
    user_id = session.get('doctor_id')
    if not user_id:
        flash("Giriş yapmanız gerekiyor!", "danger")
        return redirect(url_for('login'))

    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.id, d.name, d.department, d.start_time, d.end_time
        FROM doctors d
        JOIN users u ON d.user_id = u.id
        WHERE u.id = ?
    """, (user_id,))
    doctor = cursor.fetchone()
    print(doctor)

    cursor.execute("SELECT id, name FROM departments")
    departments = cursor.fetchall()

    cursor.execute("SELECT department FROM doctors WHERE id=?",(user_id,))
    doctor_department=cursor.fetchall()

    cursor.execute("SELECT start_time FROM doctors WHERE id=?",(user_id,))
    doctor_start_time=cursor.fetchall()

    cursor.execute("SELECT end_time FROM doctors WHERE id=?",(user_id,))
    doctor_end_time=cursor.fetchall()

    if request.method == 'POST':
        department = request.form.get('department')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        if not (start_time and end_time):
            flash("Çalışma saatlerini belirtmeniz gerekiyor!", "danger")
        elif start_time >= end_time:
            flash("Başlangıç saati, bitiş saatinden önce olmalıdır!", "danger")
        else:
            cursor.execute("""
                UPDATE doctors
                SET department = ?, start_time = ?, end_time = ?
                WHERE id = ?
            """, (department, start_time, end_time, user_id))
            conn.commit()
            flash("Profil başarıyla güncellendi!", "success")
            conn.close()
            return redirect(url_for('admin_dashboard'))

    conn.close()
    return render_template('edit_doctor_profile_admin.html', doctor=doctor, departments=departments, doctor_department=doctor_department,
                           doctor_start_time=doctor_start_time,doctor_end_time=doctor_end_time)


def update_appointment_status():
    today = datetime.datetime.now().date()
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE appointments 
        SET status = 'pasif'
        WHERE date < ? AND status = 'aktif'
    """, (today,))
    conn.commit()
    conn.close()

@app.before_request
def before_request():
    update_appointment_status()

@app.route('/toggle_user_status/<int:user_id>', methods=['POST'])
def toggle_user_status(user_id):
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT status FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    
    if user:
        new_status = 'aktif' if user[0] == 'pasif' else 'pasif'
        cursor.execute("UPDATE users SET status = ? WHERE id = ?", (new_status, user_id))
        conn.commit()
        flash(f"Kullanıcı durumu '{new_status}' olarak güncellendi!", "success")
    
    conn.close()
    return redirect(url_for('admin_users'))


@app.route('/admin/users', methods=['GET', 'POST'])
def admin_users():
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('admin_users.html', users=users)

@app.route('/admin/doctors', methods=['GET', 'POST'])
def admin_doctors():
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.id, d.name, dept.name AS department_name, u.email, d.start_time, d.end_time
        FROM doctors d
        LEFT JOIN departments dept ON d.department = dept.name
        JOIN users u ON d.user_id = u.id
    """)
    doctors = cursor.fetchall()

    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()
    conn.close()

    return render_template('admin_doctors.html', doctors=doctors, departments=departments)


@app.route('/admin/appointments')
def admin_appointments():
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments WHERE status = 'aktif'")
    active_appointments = cursor.fetchall()
    cursor.execute("SELECT * FROM appointments WHERE status = 'pasif'")
    passive_appointments = cursor.fetchall()
    conn.close()
    return render_template('admin_appointments.html', active_appointments=active_appointments, passive_appointments=passive_appointments)

@app.route('/admin/departments', methods=['GET', 'POST'])
def admin_departments():
    conn = sqlite3.connect("hospital.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM departments")
    departments = cursor.fetchall()
    conn.close()
    return render_template('admin_departments.html', departments=departments)

if __name__ == '__main__':
    app.run(debug=True)  
