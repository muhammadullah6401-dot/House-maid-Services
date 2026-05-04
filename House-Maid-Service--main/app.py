import os
from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "secret123"

# =========================
# DATABASE FIX (LOCAL + VERCEL)
# =========================
if os.environ.get("VERCEL"):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/database.db'
else:
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================
# DATABASE MODELS
# =========================
class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    role = db.Column(db.String(20), default="admin")

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    service = db.Column(db.String(100))
    date = db.Column(db.String(20))
    time = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Pending")

# =========================
# LANGUAGE
# =========================
@app.before_request
def set_default_language():
    if 'lang' not in session:
        session['lang'] = 'en'

translations = {
    "en": {
        "title": "Home Services",
        "book": "Book Now",
        "name": "Name",
        "phone": "Phone",
        "service": "Service"
    },
    "ar": {
        "title": "خدمات المنزل",
        "book": "احجز الآن",
        "name": "الاسم",
        "phone": "الهاتف",
        "service": "الخدمة"
    }
}

# =========================
# ROUTES
# =========================

@app.route('/')
def home():
    lang = session.get('lang', 'en')
    texts = translations[lang]
    return render_template('index.html', texts=texts)

@app.route('/book', methods=['POST'])
def book():
    try:
        data = request.form
        new_booking = Booking(
            name=data['name'],
            phone=data['phone'],
            service=data['service'],
            date=data['date'],
            time=data['time']
        )
        db.session.add(new_booking)
        db.session.commit()
        return "Booking Submitted Successfully!"
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admin = Admin.query.filter_by(username=username).first()

        if admin and check_password_hash(admin.password, password):
            session['admin'] = True
            session['admin_id'] = admin.id
            session['role'] = admin.role
            return redirect('/dashboard')
        else:
            flash("Invalid credentials!", "danger")

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect('/admin')

    bookings = Booking.query.all()
    admins = Admin.query.all()

    for b in bookings:
        try:
            dt = datetime.strptime(b.time, "%H:%M")
            b.time = dt.strftime("%I:%M %p")
        except:
            pass

    total_bookings = len(bookings)
    today_bookings = len([b for b in bookings if b.date == date.today().strftime("%Y-%m-%d")])
    pending = len([b for b in bookings if b.status == "Pending"])
    accepted = len([b for b in bookings if b.status == "Accepted"])

    return render_template('admin.html',
                           bookings=bookings,
                           admins=admins,
                           total_bookings=total_bookings,
                           today_bookings=today_bookings,
                           pending=pending,
                           accepted=accepted)

@app.route('/accept/<int:id>')
def accept_booking(id):
    booking = Booking.query.get(id)
    if booking:
        booking.status = "Accepted"
        db.session.commit()
    return redirect('/dashboard')

@app.route('/delete_booking/<int:id>')
def delete_booking(id):
    booking = Booking.query.get(id)
    if booking:
        db.session.delete(booking)
        db.session.commit()
    return redirect('/dashboard')

@app.route('/add_admin', methods=['POST'])
def add_admin():
    if 'admin' not in session or session['role'] != 'main':
        flash("Only Main Admin can add admins", "danger")
        return redirect('/dashboard')

    username = request.form['username']
    password = generate_password_hash(request.form['password'])
    role = request.form.get('role', 'admin')

    new_admin = Admin(username=username, password=password, role=role)
    db.session.add(new_admin)
    db.session.commit()

    return redirect('/dashboard')

@app.route('/delete_admin/<int:id>')
def delete_admin(id):
    if 'admin' not in session or session['role'] != 'main':
        flash("Only Main Admin can delete admins", "danger")
        return redirect('/dashboard')

    admin = Admin.query.get(id)
    if admin and admin.role != 'main':
        db.session.delete(admin)
        db.session.commit()

    return redirect('/dashboard')

@app.route('/change_main_admin', methods=['POST'])
def change_main_admin():
    if 'admin' not in session or session['role'] != 'main':
        flash("Only Main Admin can change credentials", "danger")
        return redirect('/dashboard')

    main_admin = Admin.query.filter_by(role='main').first()
    if main_admin:
        main_admin.username = request.form['username']
        main_admin.password = generate_password_hash(request.form['password'])
        db.session.commit()

    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/admin')

@app.route('/set_language/<lang>')
def set_language(lang):
    session['lang'] = lang
    return redirect(request.referrer or '/')

# =========================
# CREATE DATABASE
# =========================
with app.app_context():
    db.create_all()

    if not Admin.query.filter_by(role='main').first():
        main_admin = Admin(
            username="admin",
            password=generate_password_hash("1234"),
            role="main"
        )
        db.session.add(main_admin)
        db.session.commit()

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
