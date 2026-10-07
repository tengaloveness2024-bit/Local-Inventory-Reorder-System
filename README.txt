LOCAL INVENTORY & AUTOMATED REORDER MANAGEMENT SYSTEM
COMS3204 SYSTEMS ANALYSIS AND DESIGN

Student: Tenga Loveness
Candidate Number: 24.22.249
Intake: ECD 22

1. SYSTEM OVERVIEW
This system is a web-based Local Inventory and Automated Reorder Management System designed to help an organisation manage products, suppliers, stock movements and automatic reordering.

2. MAIN FEATURES
- Secure user login and authentication
- Administrator and normal user roles
- Product management
- Supplier management
- Stock-in management
- Stock-out management
- Automatic low-stock detection
- Automated reorder creation
- Reorder status management
- Inventory reports
- Dashboard statistics
- Input validation
- Negative-stock prevention
- Password hashing
- Responsive web interface
- Database storage

3. TECHNOLOGIES USED
Frontend:
HTML5
CSS3
JavaScript

Backend:
Python
Flask

Database:
SQLite

Security:
Password hashing
Session-based authentication
Role-based access control
Input validation
Negative-stock prevention
HTML escaping

4. DATABASE
The system uses SQLite to store:
- Users
- Suppliers
- Products
- Stock movements
- Reorders

5. DEFAULT ADMIN ACCOUNT
Username: admin
Password: admin123

6. NORMAL USER TEST ACCOUNT
Username: staff
Password: staff123

7. HOW TO RUN THE SYSTEM
Open Command Prompt in the project folder.

Run:

py app.py

Open a web browser and visit:

http://127.0.0.1:5000/

8. AUTOMATIC REORDER
When the quantity of a product becomes equal to or lower than its reorder level, the administrator can run the low-stock check. The system automatically creates a pending reorder request where one does not already exist.

9. STOCK CONTROL
The system prevents stock-out transactions that would cause the available stock to become negative.

10. REPORTING
The reports module displays product quantities, reorder levels, stock value and low-stock status.

11. USER MANAGEMENT
Administrators can create system users and assign administrator or normal-user roles.

12. PROJECT PURPOSE
The system improves inventory accuracy, reduces manual stock monitoring, identifies low-stock products and supports timely reordering.
