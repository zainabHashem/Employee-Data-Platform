"""
Employee Data Platform - Single File Flask App
------------------------------------------------
Features:
- Add employees (name, specialty, hire_date, qualification, courses, experience, certificates text)
- Upload files: CV (single) + Attachments (multiple)
- Dashboard: list + search/filter
- View / Edit / Delete employee
- Simple login (admin) with env-configurable credentials
- SQLite + SQLAlchemy

How to run (quick):
1) Python 3.10+
2) pip install -r requirements.txt  (see requirements block below)
3) Create folder `uploads/`
4) python app.py
5) Open http://127.0.0.1:5000  (login: admin / admin123 by default)

requirements.txt
-----------------
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Werkzeug==3.0.3
python-dotenv==1.0.1

Optional: create a .env file to override defaults:
ADMIN_USER=admin
ADMIN_PASS=admin123
SECRET_KEY=change-me
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH_MB=20
"""
from __future__ import annotations
import os
import json
from datetime import datetime
from pathlib import Path

from flask import (
    Flask, request, redirect, url_for, render_template_string, flash, session,
    send_from_directory, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# --------------------------- Config ---------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_UPLOAD = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg", "webp", "xlsx", "xls"}

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret-change-me"),
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{BASE_DIR / 'employees.db'}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=DEFAULT_UPLOAD,
)

max_mb = float(os.getenv("MAX_CONTENT_LENGTH_MB", "20"))
app.config["MAX_CONTENT_LENGTH"] = int(max_mb * 1024 * 1024)

Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

db = SQLAlchemy(app)

# --------------------------- Models ---------------------------
class Employee(db.Model):
    __tablename__ = "employees"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    specialty = db.Column(db.String(200), nullable=True)
    hire_date = db.Column(db.Date, nullable=True)
    qualification = db.Column(db.String(200), nullable=True)
    courses = db.Column(db.Text, nullable=True)  # free text or comma-separated
    experience = db.Column(db.Text, nullable=True)
    certificates_text = db.Column(db.Text, nullable=True)
    cv_filename = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    files = db.relationship("EmployeeFile", backref="employee", cascade="all, delete-orphan")

class EmployeeFile(db.Model):
    __tablename__ = "employee_files"
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    filename = db.Column(db.String(300), nullable=False)
    label = db.Column(db.String(200), nullable=True)  # e.g., "Certificate" or "Course"
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

# --------------------------- Auth Helpers ---------------------------
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "admin123")

from functools import wraps

def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapper

# --------------------------- File Helpers ---------------------------

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_file(file_storage, subdir: str) -> str | None:
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename):
        raise ValueError("نوع الملف غير مسموح")
    filename = secure_filename(file_storage.filename)
    upload_root = Path(app.config["UPLOAD_FOLDER"]) / subdir
    upload_root.mkdir(parents=True, exist_ok=True)
    dest = upload_root / filename
    # Ensure unique filename
    i = 1
    stem = dest.stem
    suffix = dest.suffix
    while dest.exists():
        dest = upload_root / f"{stem}_{i}{suffix}"
        i += 1
    file_storage.save(dest)
    return str(dest.relative_to(app.config["UPLOAD_FOLDER"]))

# --------------------------- Routes ---------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["logged_in"] = True
            flash("تم تسجيل الدخول بنجاح", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("بيانات الدخول غير صحيحة", "danger")
    return render_template_string(TPL_LOGIN)

@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("تم تسجيل الخروج", "info")
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    q = request.args.get("q", "").strip()
    specialty = request.args.get("specialty", "").strip()
    query = Employee.query
    if q:
        like = f"%{q}%"
        query = query.filter((Employee.name.ilike(like)) | (Employee.qualification.ilike(like)))
    if specialty:
        query = query.filter(Employee.specialty.ilike(f"%{specialty}%"))
    employees = query.order_by(Employee.created_at.desc()).all()
    return render_template_string(TPL_DASHBOARD, employees=employees, q=q, specialty=specialty, **tpl_ctx())

@app.route("/employees/new", methods=["GET", "POST"])
@login_required
def employee_new():
    if request.method == "POST":
        try:
            emp = Employee(
                name=request.form.get("name", "").strip(),
                specialty=request.form.get("specialty", "").strip(),
                qualification=request.form.get("qualification", "").strip(),
                courses=request.form.get("courses", "").strip(),
                experience=request.form.get("experience", "").strip(),
                certificates_text=request.form.get("certificates_text", "").strip(),
            )
            hire_date_raw = request.form.get("hire_date")
            if hire_date_raw:
                try:
                    emp.hire_date = datetime.strptime(hire_date_raw, "%Y-%m-%d").date()
                except ValueError:
                    flash("صيغة تاريخ التعيين غير صحيحة", "warning")

            # Save CV (single)
            cv_file = request.files.get("cv_file")
            if cv_file and cv_file.filename:
                emp.cv_filename = save_file(cv_file, subdir="cv")

            db.session.add(emp)
            db.session.commit()

            # Save attachments (multiple)
            attachments = request.files.getlist("attachments")
            label = request.form.get("attachment_label", "مرفق")
            for f in attachments:
                if f and f.filename:
                    rel = save_file(f, subdir=f"emp_{emp.id}")
                    db.session.add(EmployeeFile(employee_id=emp.id, filename=rel, label=label))
            db.session.commit()

            flash("تم إضافة الموظف بنجاح", "success")
            return redirect(url_for("dashboard"))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"خطأ في حفظ البيانات: {str(e)}", "danger")
    return render_template_string(TPL_EMP_FORM, emp=None, **tpl_ctx())

@app.route("/employees/<int:emp_id>")
@login_required
def employee_view(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    return render_template_string(TPL_EMP_VIEW, emp=emp, **tpl_ctx())

@app.route("/employees/<int:emp_id>/edit", methods=["GET", "POST"])
@login_required
def employee_edit(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    if request.method == "POST":
        try:
            emp.name = request.form.get("name", "").strip()
            emp.specialty = request.form.get("specialty", "").strip()
            emp.qualification = request.form.get("qualification", "").strip()
            emp.courses = request.form.get("courses", "").strip()
            emp.experience = request.form.get("experience", "").strip()
            emp.certificates_text = request.form.get("certificates_text", "").strip()
            hire_date_raw = request.form.get("hire_date")
            if hire_date_raw:
                try:
                    emp.hire_date = datetime.strptime(hire_date_raw, "%Y-%m-%d").date()
                except ValueError:
                    flash("صيغة تاريخ التعيين غير صحيحة", "warning")

            # Replace CV if uploaded
            cv_file = request.files.get("cv_file")
            if cv_file and cv_file.filename:
                emp.cv_filename = save_file(cv_file, subdir="cv")

            # New attachments
            attachments = request.files.getlist("attachments")
            label = request.form.get("attachment_label", "مرفق")
            for f in attachments:
                if f and f.filename:
                    rel = save_file(f, subdir=f"emp_{emp.id}")
                    db.session.add(EmployeeFile(employee_id=emp.id, filename=rel, label=label))

            db.session.commit()
            flash("تم تحديث بيانات الموظف", "success")
            return redirect(url_for("employee_view", emp_id=emp.id))
        except ValueError as e:
            flash(str(e), "danger")
        except Exception as e:
            flash(f"خطأ في تحديث البيانات: {str(e)}", "danger")
    return render_template_string(TPL_EMP_FORM, emp=emp, **tpl_ctx())

@app.route("/employees/<int:emp_id>/delete", methods=["POST"]) 
@login_required
def employee_delete(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    db.session.delete(emp)
    db.session.commit()
    flash("تم حذف الموظف", "info")
    return redirect(url_for("dashboard"))

@app.route("/files/<path:relpath>")
@login_required
def serve_file(relpath):
    # Security: serve only within upload folder
    uploads = Path(app.config["UPLOAD_FOLDER"]) 
    rel = Path(relpath)
    target = uploads / rel
    try:
        target.resolve().relative_to(uploads.resolve())
    except Exception:
        abort(403)
    if not target.exists():
        abort(404)
    return send_from_directory(uploads, relpath, as_attachment=False)

@app.route("/employees/<int:emp_id>/file/<int:file_id>/delete", methods=["POST"])
@login_required
def delete_file(emp_id, file_id):
    emp_file = EmployeeFile.query.filter_by(id=file_id, employee_id=emp_id).first_or_404()
    db.session.delete(emp_file)
    db.session.commit()
    flash("تم حذف الملف", "info")
    return redirect(url_for("employee_edit", emp_id=emp_id))

# --------------------------- Helper Functions ---------------------------

def tpl_ctx():
    return {
        "app_name": "نظام بيانات الموظفين",
        "max_mb": int(app.config["MAX_CONTENT_LENGTH"] / (1024*1024)),
    }

# --------------------------- Templates ---------------------------

TPL_LOGIN = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>تسجيل الدخول - نظام بيانات الموظفين</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; }
        .login-container { min-height: 100vh; }
    </style>
</head>
<body>
    <div class="container-fluid login-container d-flex align-items-center justify-content-center">
        <div class="row w-100">
            <div class="col-md-4 mx-auto">
                <div class="card shadow">
                    <div class="card-body p-4">
                        <div class="text-center mb-4">
                            <h3 class="card-title">نظام بيانات الموظفين</h3>
                            <p class="text-muted">تسجيل الدخول للوحة التحكم</p>
                        </div>
                        
                        {% with messages = get_flashed_messages(with_categories=true) %}
                            {% if messages %}
                                {% for category, message in messages %}
                                    <div class="alert alert-{{ 'danger' if category == 'danger' else 'success' }} alert-dismissible fade show">
                                        {{ message }}
                                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                                    </div>
                                {% endfor %}
                            {% endif %}
                        {% endwith %}
                        
                        <form method="post">
                            <div class="mb-3">
                                <label for="username" class="form-label">اسم المستخدم</label>
                                <input type="text" class="form-control" id="username" name="username" required>
                            </div>
                            <div class="mb-3">
                                <label for="password" class="form-label">كلمة المرور</label>
                                <input type="password" class="form-control" id="password" name="password" required>
                            </div>
                            <div class="d-grid">
                                <button type="submit" class="btn btn-primary">دخول</button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

TPL_DASHBOARD = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>لوحة التحكم - نظام بيانات الموظفين</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
</head>
<body class="bg-light">
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="bi bi-people-fill"></i>
                نظام بيانات الموظفين
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('logout') }}">
                    <i class="bi bi-box-arrow-right"></i>
                    تسجيل الخروج
                </a>
            </div>
        </div>
    </nav>

    <div class="container">
        <!-- Flash Messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'danger' else 'success' if category == 'success' else 'info' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- Header -->
        <div class="row mb-4">
            <div class="col">
                <div class="d-flex justify-content-between align-items-center">
                    <h2><i class="bi bi-speedometer2"></i> لوحة التحكم</h2>
                    <a href="{{ url_for('employee_new') }}" class="btn btn-success">
                        <i class="bi bi-plus-circle"></i>
                        إضافة موظف جديد
                    </a>
                </div>
            </div>
        </div>

        <!-- Search and Filter -->
        <div class="card shadow-sm mb-4">
            <div class="card-body">
                <h5 class="card-title"><i class="bi bi-search"></i> البحث والتصفية</h5>
                <form class="row g-3" method="get">
                    <div class="col-md-5">
                        <label class="form-label">بحث (الاسم/المؤهل)</label>
                        <input type="text" class="form-control" name="q" value="{{ q }}" placeholder="ابحث في الأسماء والمؤهلات...">
                    </div>
                    <div class="col-md-5">
                        <label class="form-label">التخصص</label>
                        <input type="text" class="form-control" name="specialty" value="{{ specialty }}" placeholder="مثال: موارد بشرية، محاسبة...">
                    </div>
                    <div class="col-md-2 d-flex align-items-end">
                        <div class="w-100">
                            <button type="submit" class="btn btn-primary w-100">
                                <i class="bi bi-search"></i> بحث
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>

        <!-- Employees List -->
        <div class="row">
            <div class="col-12">
                {% if employees %}
                    <div class="card shadow-sm">
                        <div class="card-header">
                            <h5 class="mb-0"><i class="bi bi-people"></i> قائمة الموظفين ({{ employees|length }} موظف)</h5>
                        </div>
                        <div class="card-body p-0">
                            <div class="table-responsive">
                                <table class="table table-hover mb-0">
                                    <thead class="table-light">
                                        <tr>
                                            <th>الاسم</th>
                                            <th>التخصص</th>
                                            <th>المؤهل</th>
                                            <th>تاريخ التعيين</th>
                                            <th>الإجراءات</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {% for emp in employees %}
                                            <tr>
                                                <td>
                                                    <strong>{{ emp.name }}</strong>
                                                    {% if emp.cv_filename %}
                                                        <small class="text-success">
                                                            <i class="bi bi-file-earmark-pdf"></i>
                                                        </small>
                                                    {% endif %}
                                                    {% if emp.files %}
                                                        <small class="text-info">
                                                            <i class="bi bi-paperclip"></i> {{ emp.files|length }}
                                                        </small>
                                                    {% endif %}
                                                </td>
                                                <td>{{ emp.specialty or '—' }}</td>
                                                <td>{{ emp.qualification or '—' }}</td>
                                                <td>
                                                    {% if emp.hire_date %}
                                                        {{ emp.hire_date.strftime('%Y/%m/%d') }}
                                                    {% else %}
                                                        —
                                                    {% endif %}
                                                </td>
                                                <td>
                                                    <div class="btn-group btn-group-sm">
                                                        <a href="{{ url_for('employee_view', emp_id=emp.id) }}" 
                                                           class="btn btn-outline-info" title="عرض">
                                                            <i class="bi bi-eye"></i>
                                                        </a>
                                                        <a href="{{ url_for('employee_edit', emp_id=emp.id) }}" 
                                                           class="btn btn-outline-secondary" title="تعديل">
                                                            <i class="bi bi-pencil"></i>
                                                        </a>
                                                        <form method="post" action="{{ url_for('employee_delete', emp_id=emp.id) }}" 
                                                              style="display: inline;"
                                                              onsubmit="return confirm('هل أنت متأكد من حذف الموظف {{ emp.name }}؟');">
                                                            <button type="submit" class="btn btn-outline-danger" title="حذف">
                                                                <i class="bi bi-trash"></i>
                                                            </button>
                                                        </form>
                                                    </div>
                                                </td>
                                            </tr>
                                        {% endfor %}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                {% else %}
                    <div class="card shadow-sm">
                        <div class="card-body text-center py-5">
                            <i class="bi bi-people text-muted" style="font-size: 4rem;"></i>
                            <h4 class="mt-3 text-muted">لا توجد بيانات موظفين</h4>
                            <p class="text-muted">ابدأ بإضافة موظف جديد لبناء قاعدة البيانات</p>
                            <a href="{{ url_for('employee_new') }}" class="btn btn-success">
                                <i class="bi bi-plus-circle"></i>
                                إضافة أول موظف
                            </a>
                        </div>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

TPL_EMP_FORM = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ 'تعديل' if emp else 'إضافة' }} موظف - نظام بيانات الموظفين</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
</head>
<body class="bg-light">
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="bi bi-people-fill"></i>
                نظام بيانات الموظفين
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('logout') }}">
                    <i class="bi bi-box-arrow-right"></i>
                    تسجيل الخروج
                </a>
            </div>
        </div>
    </nav>

    <div class="container">
        <!-- Flash Messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'danger' else 'success' if category == 'success' else 'warning' if category == 'warning' else 'info' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row">
            <div class="col-12">
                <div class="card shadow-sm">
                    <div class="card-header">
                        <h4 class="mb-0">
                            <i class="bi bi-{{ 'pencil' if emp else 'plus-circle' }}"></i>
                            {{ 'تعديل بيانات الموظف' if emp else 'إضافة موظف جديد' }}
                        </h4>
                    </div>
                    <div class="card-body">
                        <form method="post" enctype="multipart/form-data">
                            <!-- Basic Information -->
                            <h5 class="border-bottom pb-2 mb-3">
                                <i class="bi bi-person-badge"></i>
                                البيانات الأساسية
                            </h5>
                            <div class="row g-3 mb-4">
                                <div class="col-md-6">
                                    <label class="form-label">الاسم الكامل <span class="text-danger">*</span></label>
                                    <input type="text" class="form-control" name="name" 
                                           value="{{ emp.name if emp else '' }}" required
                                           placeholder="أدخل الاسم الكامل للموظف">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">التخصص</label>
                                    <input type="text" class="form-control" name="specialty" 
                                           value="{{ emp.specialty if emp else '' }}"
                                           placeholder="مثال: موارد بشرية، محاسبة، هندسة">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">تاريخ التعيين</label>
                                    <input type="date" class="form-control" name="hire_date" 
                                           value="{{ emp.hire_date.strftime('%Y-%m-%d') if emp and emp.hire_date else '' }}">
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">المؤهل العلمي</label>
                                    <input type="text" class="form-control" name="qualification" 
                                           value="{{ emp.qualification if emp else '' }}"
                                           placeholder="مثال: بكالوريوس هندسة، ماجستير إدارة أعمال">
                                </div>
                            </div>

                            <!-- Experience and Skills -->
                            <h5 class="border-bottom pb-2 mb-3">
                                <i class="bi bi-award"></i>
                                الخبرات والمهارات
                            </h5>
                            <div class="row g-3 mb-4">
                                <div class="col-md-6">
                                    <label class="form-label">الدورات التدريبية</label>
                                    <textarea class="form-control" name="courses" rows="4"
                                              placeholder="اذكر الدورات التدريبية التي حصل عليها الموظف...">{{ emp.courses if emp else '' }}</textarea>
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">الخبرات العملية</label>
                                    <textarea class="form-control" name="experience" rows="4"
                                              placeholder="اذكر الخبرات العملية والوظائف السابقة...">{{ emp.experience if emp else '' }}</textarea>
                                </div>
                                <div class="col-12">
                                    <label class="form-label">الشهادات والتقديرات</label>
                                    <textarea class="form-control" name="certificates_text" rows="3"
                                              placeholder="اذكر الشهادات والتقديرات التي حصل عليها الموظف...">{{ emp.certificates_text if emp else '' }}</textarea>
                                </div>
                            </div>

                            <!-- File Uploads -->
                            <h5 class="border-bottom pb-2 mb-3">
                                <i class="bi bi-files"></i>
                                الملفات والمرفقات
                            </h5>
                            <div class="row g-3 mb-4">
                                <div class="col-md-6">
                                    <label class="form-label">السيرة الذاتية (PDF/Word)</label>
                                    <input type="file" class="form-control" name="cv_file" 
                                           accept=".pdf,.doc,.docx">
                                    <div class="form-text">
                                        أنواع الملفات المسموحة: PDF, DOC, DOCX (حد أقصى {{ max_mb }}MB)
                                    </div>
                                    {% if emp and emp.cv_filename %}
                                        <div class="mt-2">
                                            <small class="text-success">
                                                <i class="bi bi-file-earmark-pdf"></i>
                                                <a href="{{ url_for('serve_file', relpath=emp.cv_filename) }}" 
                                                   target="_blank" class="text-decoration-none">
                                                    عرض السيرة الذاتية الحالية
                                                </a>
                                            </small>
                                        </div>
                                    {% endif %}
                                </div>
                                <div class="col-md-6">
                                    <label class="form-label">مرفقات إضافية (شهادات/دورات)</label>
                                    <input type="file" class="form-control mb-2" name="attachments" multiple
                                           accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.xlsx,.xls">
                                    <input type="text" class="form-control" name="attachment_label" 
                                           placeholder="تصنيف المرفقات (اختياري)" value="مرفق">
                                    <div class="form-text">
                                        يمكنك تحديد عدة ملفات. أنواع مسموحة: PDF, Word, Excel, صور
                                    </div>
                                </div>
                            </div>

                            <!-- Existing Files -->
                            {% if emp and emp.files %}
                                <h6 class="mb-3">
                                    <i class="bi bi-paperclip"></i>
                                    المرفقات الموجودة
                                </h6>
                                <div class="row g-2 mb-4">
                                    {% for f in emp.files %}
                                        <div class="col-md-6">
                                            <div class="card card-body bg-light">
                                                <div class="d-flex justify-content-between align-items-center">
                                                    <div>
                                                        <strong>{{ f.label or 'مرفق' }}</strong><br>
                                                        <small class="text-muted">{{ f.filename.split('/')[-1] }}</small>
                                                    </div>
                                                    <div class="btn-group btn-group-sm">
                                                        <a href="{{ url_for('serve_file', relpath=f.filename) }}" 
                                                           target="_blank" class="btn btn-outline-primary">
                                                            <i class="bi bi-eye"></i>
                                                        </a>
                                                        <form method="post" style="display: inline;" 
                                                              action="{{ url_for('delete_file', emp_id=emp.id, file_id=f.id) }}"
                                                              onsubmit="return confirm('حذف هذا الملف؟');">
                                                            <button type="submit" class="btn btn-outline-danger">
                                                                <i class="bi bi-trash"></i>
                                                            </button>
                                                        </form>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    {% endfor %}
                                </div>
                            {% endif %}

                            <!-- Action Buttons -->
                            <div class="d-flex gap-2 pt-3 border-top">
                                <button type="submit" class="btn btn-success">
                                    <i class="bi bi-check-circle"></i>
                                    {{ 'حفظ التعديلات' if emp else 'إضافة الموظف' }}
                                </button>
                                <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">
                                    <i class="bi bi-arrow-right"></i>
                                    رجوع للقائمة
                                </a>
                                {% if emp %}
                                    <a href="{{ url_for('employee_view', emp_id=emp.id) }}" class="btn btn-outline-info">
                                        <i class="bi bi-eye"></i>
                                        عرض البيانات
                                    </a>
                                {% endif %}
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

TPL_EMP_VIEW = """
<!doctype html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ emp.name }} - نظام بيانات الموظفين</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css" rel="stylesheet">
</head>
<body class="bg-light">
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('dashboard') }}">
                <i class="bi bi-people-fill"></i>
                نظام بيانات الموظفين
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="{{ url_for('logout') }}">
                    <i class="bi bi-box-arrow-right"></i>
                    تسجيل الخروج
                </a>
            </div>
        </div>
    </nav>

    <div class="container">
        <!-- Flash Messages -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ 'danger' if category == 'danger' else 'success' if category == 'success' else 'info' }} alert-dismissible fade show">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="row">
            <div class="col-12">
                <div class="card shadow-sm">
                    <div class="card-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h4 class="mb-0">
                                <i class="bi bi-person-circle"></i>
                                {{ emp.name }}
                            </h4>
                            <div class="btn-group">
                                <a href="{{ url_for('employee_edit', emp_id=emp.id) }}" class="btn btn-outline-secondary">
                                    <i class="bi bi-pencil"></i>
                                    تعديل
                                </a>
                                <form method="post" action="{{ url_for('employee_delete', emp_id=emp.id) }}" 
                                      style="display: inline;"
                                      onsubmit="return confirm('هل أنت متأكد من حذف الموظف {{ emp.name }}؟\nسيتم حذف جميع الملفات المرتبطة به!');">
                                    <button type="submit" class="btn btn-outline-danger">
                                        <i class="bi bi-trash"></i>
                                        حذف
                                    </button>
                                </form>
                            </div>
                        </div>
                    </div>
                    <div class="card-body">
                        <!-- Basic Information -->
                        <h5 class="border-bottom pb-2 mb-3">
                            <i class="bi bi-person-badge"></i>
                            البيانات الأساسية
                        </h5>
                        <div class="row g-3 mb-4">
                            <div class="col-md-6">
                                <strong class="text-muted">الاسم:</strong>
                                <div>{{ emp.name }}</div>
                            </div>
                            <div class="col-md-6">
                                <strong class="text-muted">التخصص:</strong>
                                <div>{{ emp.specialty or '—' }}</div>
                            </div>
                            <div class="col-md-6">
                                <strong class="text-muted">تاريخ التعيين:</strong>
                                <div>
                                    {% if emp.hire_date %}
                                        {{ emp.hire_date.strftime('%Y/%m/%d') }}
                                    {% else %}
                                        —
                                    {% endif %}
                                </div>
                            </div>
                            <div class="col-md-6">
                                <strong class="text-muted">المؤهل العلمي:</strong>
                                <div>{{ emp.qualification or '—' }}</div>
                            </div>
                        </div>

                        <!-- Experience and Skills -->
                        <h5 class="border-bottom pb-2 mb-3">
                            <i class="bi bi-award"></i>
                            الخبرات والمهارات
                        </h5>
                        <div class="row g-3 mb-4">
                            <div class="col-md-6">
                                <strong class="text-muted">الدورات التدريبية:</strong>
                                <div class="mt-1">
                                    {% if emp.courses %}
                                        <div class="border p-2 rounded bg-light">
                                            {{ emp.courses|replace('\n', '<br>')|safe }}
                                        </div>
                                    {% else %}
                                        —
                                    {% endif %}
                                </div>
                            </div>
                            <div class="col-md-6">
                                <strong class="text-muted">الخبرات العملية:</strong>
                                <div class="mt-1">
                                    {% if emp.experience %}
                                        <div class="border p-2 rounded bg-light">
                                            {{ emp.experience|replace('\n', '<br>')|safe }}
                                        </div>
                                    {% else %}
                                        —
                                    {% endif %}
                                </div>
                            </div>
                            <div class="col-12">
                                <strong class="text-muted">الشهادات والتقديرات:</strong>
                                <div class="mt-1">
                                    {% if emp.certificates_text %}
                                        <div class="border p-2 rounded bg-light">
                                            {{ emp.certificates_text|replace('\n', '<br>')|safe }}
                                        </div>
                                    {% else %}
                                        —
                                    {% endif %}
                                </div>
                            </div>
                        </div>

                        <!-- Files and Attachments -->
                        <h5 class="border-bottom pb-2 mb-3">
                            <i class="bi bi-files"></i>
                            الملفات والمرفقات
                        </h5>
                        
                        <!-- CV -->
                        <div class="row g-3 mb-3">
                            <div class="col-md-6">
                                <strong class="text-muted">السيرة الذاتية:</strong>
                                <div class="mt-1">
                                    {% if emp.cv_filename %}
                                        <a href="{{ url_for('serve_file', relpath=emp.cv_filename) }}" 
                                           target="_blank" class="btn btn-outline-primary btn-sm">
                                            <i class="bi bi-file-earmark-pdf"></i>
                                            فتح السيرة الذاتية
                                        </a>
                                    {% else %}
                                        <span class="text-muted">لم يتم رفع السيرة الذاتية</span>
                                    {% endif %}
                                </div>
                            </div>
                        </div>

                        <!-- Attachments -->
                        {% if emp.files %}
                            <div class="row g-3">
                                <div class="col-12">
                                    <strong class="text-muted">المرفقات الإضافية:</strong>
                                    <div class="row g-2 mt-1">
                                        {% for f in emp.files %}
                                            <div class="col-md-6 col-lg-4">
                                                <div class="card card-body bg-light h-100">
                                                    <div class="d-flex flex-column">
                                                        <div class="mb-2">
                                                            <strong class="text-primary">{{ f.label or 'مرفق' }}</strong>
                                                        </div>
                                                        <div class="mb-2 small text-muted">
                                                            {{ f.filename.split('/')[-1] }}
                                                        </div>
                                                        <div class="small text-muted mb-2">
                                                            <i class="bi bi-calendar"></i>
                                                            {{ f.uploaded_at.strftime('%Y/%m/%d') }}
                                                        </div>
                                                        <div class="mt-auto">
                                                            <a href="{{ url_for('serve_file', relpath=f.filename) }}" 
                                                               target="_blank" class="btn btn-primary btn-sm w-100">
                                                                <i class="bi bi-download"></i>
                                                                فتح/تحميل
                                                            </a>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        {% endfor %}
                                    </div>
                                </div>
                            </div>
                        {% else %}
                            <div class="text-muted">لا توجد مرفقات إضافية</div>
                        {% endif %}

                        <!-- Timestamps -->
                        <div class="row g-3 mt-4 pt-3 border-top">
                            <div class="col-md-6">
                                <small class="text-muted">
                                    <i class="bi bi-plus-circle"></i>
                                    تاريخ الإضافة: {{ emp.created_at.strftime('%Y/%m/%d - %H:%M') }}
                                </small>
                            </div>
                            <div class="col-md-6">
                                <small class="text-muted">
                                    <i class="bi bi-pencil-square"></i>
                                    آخر تحديث: {{ emp.updated_at.strftime('%Y/%m/%d - %H:%M') }}
                                </small>
                            </div>
                        </div>

                        <!-- Action Buttons -->
                        <div class="d-flex gap-2 pt-3 border-top">
                            <a href="{{ url_for('dashboard') }}" class="btn btn-secondary">
                                <i class="bi bi-arrow-right"></i>
                                رجوع للقائمة
                            </a>
                            <a href="{{ url_for('employee_edit', emp_id=emp.id) }}" class="btn btn-primary">
                                <i class="bi bi-pencil"></i>
                                تعديل البيانات
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# --------------------------- Init DB ---------------------------
with app.app_context():
    db.create_all()

# --------------------------- Run ---------------------------
if __name__ == "__main__":
    app.run(debug=True)  # set debug=False in production