# Employee-Data-Platform

A comprehensive employee management system built with Flask, featuring an Arabic RTL interface, SQLite database, and file management capabilities.

## 🚀 Key Features

### ✅ Employee Management
- **Add new employees** with comprehensive data fields
- **Edit and delete** existing employee records
- **Detailed employee profiles** with full information display
- **Advanced search and filtering** capabilities

### 📁 File Management
- **CV uploads** (PDF, Word documents)
- **Multiple attachments** (certificates, courses, documents)
- **View and download** all uploaded files
- **Individual file deletion** capabilities
- **Secure file handling** with access control

### 🔐 Security System
- **Secure admin authentication** system
- **Protected sessions** with proper expiration
- **File path protection** against unauthorized access
- **Input validation** and secure file uploads

### 🎨 Modern User Interface
- **Arabic RTL responsive design**
- **Bootstrap 5** with professional icons
- **Smooth user experience** across all devices
- **Confirmation dialogs** and visual indicators

## 📋 Supported Data Fields

### Employee Basic Information
- Full Name ⭐ (Required)
- Specialty/Department
- Hire Date
- Educational Qualification
- Training Courses
- Work Experience
- Certificates and Awards

### Supported File Types
- **CV Files**: PDF, DOC, DOCX
- **Attachments**: PDF, Word, Excel, Images (JPG, PNG, WEBP)
- **File Size Limit**: 20MB per file (configurable)

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### 1. Download Project
```bash
# Clone or download project files
git clone <repository-url>
cd employee-platform
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Linux/Mac
source venv/bin/activate
```

### 3. Install Requirements
Create `requirements.txt`:
```txt
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Werkzeug==3.0.3
python-dotenv==1.0.1
```

Install packages:
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
Create uploads directory:
```bash
mkdir uploads
```

Create `.env` file (optional):
```env
ADMIN_USER=admin
ADMIN_PASS=your_secure_password
SECRET_KEY=your_secret_key_here
UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH_MB=20
```

### 5. Run Application
```bash
python app.py
```

### 6. Access Application
Open your browser and navigate to: `http://127.0.0.1:5000`

**Default Login Credentials:**
- Username: `admin`
- Password: `admin123`

## 🗂️ Project Structure

```
employee-platform/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (optional)
├── README.md             # This file
├── employees.db          # SQLite database (auto-created)
└── uploads/              # File upload directory
    ├── cv/              # CV files
    └── emp_[id]/        # Employee-specific attachments
```

## 🔧 Configuration Options

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_USER` | `admin` | Admin username |
| `ADMIN_PASS` | `admin123` | Admin password |
| `SECRET_KEY` | `dev-secret-change-me` | Flask secret key |
| `UPLOAD_FOLDER` | `uploads` | File upload directory |
| `MAX_CONTENT_LENGTH_MB` | `20` | Maximum file size in MB |

### Allowed File Extensions
- **Documents**: PDF, DOC, DOCX, XLS, XLSX
- **Images**: PNG, JPG, JPEG, WEBP

## 📱 User Interface Pages

### 1. Login Page
- Secure authentication
- Arabic interface
- Error message display

### 2. Dashboard
- Employee list overview
- Search and filter functionality
- Quick action buttons
- Employee statistics

### 3. Add/Edit Employee
- Comprehensive form with all data fields
- File upload capabilities
- Validation and error handling
- Existing file management

### 4. Employee Profile
- Complete employee information display
- File viewing and downloading
- Quick edit and delete actions
- Activity timestamps

## 🔍 Search & Filter Features

- **Text Search**: Search by name or qualification
- **Specialty Filter**: Filter by employee specialty/department
- **Combined Filters**: Use multiple criteria simultaneously
- **Real-time Results**: Instant search results

## 💾 Database Schema

### Employees Table
- `id`: Primary key
- `name`: Employee full name (required)
- `specialty`: Job specialty/department
- `hire_date`: Employment start date
- `qualification`: Educational background
- `courses`: Training courses (text)
- `experience`: Work experience (text)
- `certificates_text`: Certificates description
- `cv_filename`: CV file path
- `created_at`: Record creation timestamp
- `updated_at`: Last modification timestamp

### Employee Files Table
- `id`: Primary key
- `employee_id`: Foreign key to employees
- `filename`: File path
- `label`: File category/description
- `uploaded_at`: Upload timestamp

## 🚀 Production Deployment

### 1. Security Considerations
```python
# In production, set debug=False
app.run(debug=False)
```

### 2. Environment Variables
Set secure values for production:
```env
SECRET_KEY=your_very_secure_secret_key
ADMIN_PASS=strong_password_here
```

### 3. Web Server Setup
Use a production WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

### 4. Reverse Proxy
Configure nginx or Apache as reverse proxy for static files and SSL.

## 🛡️ Security Features

- **CSRF Protection**: Forms protected against cross-site attacks
- **File Type Validation**: Only allowed extensions accepted
- **Path Traversal Protection**: Secure file serving
- **Session Management**: Proper login/logout handling
- **Input Sanitization**: Secure filename handling

## 🔧 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure all packages are installed
pip install -r requirements.txt
```

**2. Permission Errors**
```bash
# Check uploads directory permissions
chmod 755 uploads/
```

**3. Database Issues**
```bash
# Delete database to reset (loses all data)
rm employees.db
python app.py  # Will recreate database
```

**4. File Upload Errors**
- Check file size (max 20MB by default)
- Verify file extension is allowed
- Ensure uploads directory exists

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is open source. Feel free to use and modify according to your needs.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the configuration options
3. Create an issue in the repository

## 🔄 Version History

- **v1.0.0**: Initial release with full employee management
- **v1.1.0**: Added file management and improved UI
- **v1.2.0**: Enhanced security and Arabic RTL support

---

**Made with ❤️ for efficient employee data management**
