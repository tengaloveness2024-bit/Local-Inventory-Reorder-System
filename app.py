from flask import Flask, request, jsonify, session, send_from_directory
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pathlib import Path

app = Flask(__name__)
app.secret_key = "LOCAL_INVENTORY_SYSTEM_SECRET_KEY"

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "inventory.db"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'staff'
    );

    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT,
        email TEXT,
        address TEXT
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT,
        quantity INTEGER NOT NULL DEFAULT 0,
        reorder_level INTEGER NOT NULL DEFAULT 10,
        reorder_quantity INTEGER NOT NULL DEFAULT 20,
        supplier_id INTEGER,
        unit_price REAL DEFAULT 0,
        FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
    );

    CREATE TABLE IF NOT EXISTS stock_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        movement_type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        movement_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_id INTEGER,
        FOREIGN KEY (product_id) REFERENCES products(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS reorders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        reorder_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)

    # Default administrator
    admin = conn.execute(
        "SELECT id FROM users WHERE username = ?",
        ("admin",)
    ).fetchone()

    if admin is None:
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (
                "admin",
                generate_password_hash("admin123"),
                "admin"
            )
        )

    conn.commit()
    conn.close()


# ---------------- AUTHENTICATION ----------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return function(*args, **kwargs)

    return wrapper


# ---------------- PAGES ----------------

@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "index.html")


@app.route("/login.html")
def login_page():
    return send_from_directory(str(BASE_DIR), "login.html")


@app.route("/dashboard.html")
def dashboard_page():
    return send_from_directory(str(BASE_DIR), "dashboard.html")


@app.route("/products.html")
def products_page():
    return send_from_directory(str(BASE_DIR), "products.html")


@app.route("/suppliers.html")
def suppliers_page():
    return send_from_directory(str(BASE_DIR), "suppliers.html")


@app.route("/stock_in.html")
def stock_in_page():
    return send_from_directory(str(BASE_DIR), "stock_in.html")


@app.route("/stock_out.html")
def stock_out_page():
    return send_from_directory(str(BASE_DIR), "stock_out.html")


@app.route("/reorders.html")
def reorders_page():
    return send_from_directory(str(BASE_DIR), "reorders.html")


@app.route("/reports.html")
def reports_page():
    return send_from_directory(str(BASE_DIR), "reports.html")


@app.route("/admin.html")
def admin_page():
    return send_from_directory(str(BASE_DIR), "admin.html")



# ---------------- LOGIN ----------------

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or not password:
        return jsonify({
            "success": False,
            "error": "Username and password are required."
        }), 400

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    conn.close()

    if user and check_password_hash(user["password"], password):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        return jsonify({
            "success": True,
            "message": "Login successful",
            "username": user["username"],
            "role": user["role"]
        })

    return jsonify({
        "success": False,
        "error": "Invalid username or password."
    }), 401


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/me")
def current_user():
    if "user_id" not in session:
        return jsonify({"logged_in": False})

    return jsonify({
        "logged_in": True,
        "username": session["username"],
        "role": session["role"]
    })


# ---------------- PRODUCTS ----------------

@app.route("/api/products", methods=["GET"])
@login_required
def get_products():
    conn = get_db()

    products = conn.execute("""
        SELECT products.*, suppliers.name AS supplier_name
        FROM products
        LEFT JOIN suppliers ON products.supplier_id = suppliers.id
        ORDER BY products.id DESC
    """).fetchall()

    conn.close()

    return jsonify([dict(row) for row in products])


@app.route("/api/products", methods=["POST"])
@login_required
def create_product():
    data = request.get_json() or {}

    required = ["product_code", "name"]

    for field in required:
        if not str(data.get(field, "")).strip():
            return jsonify({
                "error": f"{field} is required."
            }), 400

    try:
        quantity = int(data.get("quantity", 0))
        reorder_level = int(data.get("reorder_level", 10))
        reorder_quantity = int(data.get("reorder_quantity", 20))
        unit_price = float(data.get("unit_price", 0))
    except (ValueError, TypeError):
        return jsonify({
            "error": "Numeric fields contain invalid values."
        }), 400

    if quantity < 0:
        return jsonify({"error": "Quantity cannot be negative."}), 400

    conn = get_db()

    try:
        conn.execute("""
            INSERT INTO products
            (product_code, name, category, quantity,
             reorder_level, reorder_quantity, supplier_id, unit_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["product_code"].strip(),
            data["name"].strip(),
            data.get("category", ""),
            quantity,
            reorder_level,
            reorder_quantity,
            data.get("supplier_id"),
            unit_price
        ))

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({
            "error": "Product code already exists."
        }), 400

    conn.close()

    return jsonify({
        "success": True,
        "message": "Product created successfully."
    }), 201


@app.route("/api/products/<int:product_id>", methods=["PUT"])
@login_required
def update_product(product_id):
    data = request.get_json() or {}

    conn = get_db()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if not product:
        conn.close()
        return jsonify({"error": "Product not found."}), 404

    try:
        quantity = int(data.get("quantity", product["quantity"]))
        reorder_level = int(
            data.get("reorder_level", product["reorder_level"])
        )
        reorder_quantity = int(
            data.get("reorder_quantity", product["reorder_quantity"])
        )
        unit_price = float(
            data.get("unit_price", product["unit_price"])
        )
    except (ValueError, TypeError):
        conn.close()
        return jsonify({"error": "Invalid numeric value."}), 400

    if quantity < 0:
        conn.close()
        return jsonify({"error": "Quantity cannot be negative."}), 400

    conn.execute("""
        UPDATE products
        SET product_code = ?,
            name = ?,
            category = ?,
            quantity = ?,
            reorder_level = ?,
            reorder_quantity = ?,
            supplier_id = ?,
            unit_price = ?
        WHERE id = ?
    """, (
        data.get("product_code", product["product_code"]),
        data.get("name", product["name"]),
        data.get("category", product["category"]),
        quantity,
        reorder_level,
        reorder_quantity,
        data.get("supplier_id", product["supplier_id"]),
        unit_price,
        product_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Product updated successfully."
    })


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
@login_required
def delete_product(product_id):
    conn = get_db()

    product = conn.execute(
        "SELECT id FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if not product:
        conn.close()
        return jsonify({"error": "Product not found."}), 404

    conn.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Product deleted successfully."
    })


# ---------------- SUPPLIERS ----------------

@app.route("/api/suppliers", methods=["GET"])
@login_required
def get_suppliers():
    conn = get_db()

    suppliers = conn.execute(
        "SELECT * FROM suppliers ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return jsonify([dict(row) for row in suppliers])


@app.route("/api/suppliers", methods=["POST"])
@login_required
def create_supplier():
    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()

    if not name:
        return jsonify({"error": "Supplier name is required."}), 400

    conn = get_db()

    conn.execute("""
        INSERT INTO suppliers (name, contact, email, address)
        VALUES (?, ?, ?, ?)
    """, (
        name,
        data.get("contact", ""),
        data.get("email", ""),
        data.get("address", "")
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Supplier added successfully."
    }), 201


@app.route("/api/suppliers/<int:supplier_id>", methods=["DELETE"])
@login_required
def delete_supplier(supplier_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM suppliers WHERE id = ?",
        (supplier_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Supplier deleted successfully."
    })


# ---------------- STOCK IN ----------------

@app.route("/api/stock-in", methods=["POST"])
@login_required
def stock_in():
    data = request.get_json() or {}

    try:
        product_id = int(data["product_id"])
        quantity = int(data["quantity"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Invalid stock-in data."}), 400

    if quantity <= 0:
        return jsonify({
            "error": "Stock-in quantity must be greater than zero."
        }), 400

    conn = get_db()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if not product:
        conn.close()
        return jsonify({"error": "Product not found."}), 404

    conn.execute(
        "UPDATE products SET quantity = quantity + ? WHERE id = ?",
        (quantity, product_id)
    )

    conn.execute("""
        INSERT INTO stock_movements
        (product_id, movement_type, quantity, user_id)
        VALUES (?, 'IN', ?, ?)
    """, (
        product_id,
        quantity,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Stock received successfully."
    })


# ---------------- STOCK OUT ----------------

@app.route("/api/stock-out", methods=["POST"])
@login_required
def stock_out():
    data = request.get_json() or {}

    try:
        product_id = int(data["product_id"])
        quantity = int(data["quantity"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Invalid stock-out data."}), 400

    if quantity <= 0:
        return jsonify({
            "error": "Stock-out quantity must be greater than zero."
        }), 400

    conn = get_db()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if not product:
        conn.close()
        return jsonify({"error": "Product not found."}), 404

    if quantity > product["quantity"]:
        conn.close()
        return jsonify({
            "error": "Insufficient stock. Negative stock is not allowed."
        }), 400

    conn.execute(
        "UPDATE products SET quantity = quantity - ? WHERE id = ?",
        (quantity, product_id)
    )

    conn.execute("""
        INSERT INTO stock_movements
        (product_id, movement_type, quantity, user_id)
        VALUES (?, 'OUT', ?, ?)
    """, (
        product_id,
        quantity,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Stock issued successfully."
    })


# ---------------- AUTOMATED REORDER ----------------

@app.route("/api/reorders", methods=["GET"])
@login_required
def get_reorders():
    conn = get_db()

    reorders = conn.execute("""
        SELECT
            reorders.id,
            reorders.quantity,
            reorders.status,
            reorders.reorder_date,
            products.product_code,
            products.name
        FROM reorders
        JOIN products ON reorders.product_id = products.id
        ORDER BY reorders.id DESC
    """).fetchall()

    conn.close()

    return jsonify([dict(row) for row in reorders])


@app.route("/api/reorders/check", methods=["POST"])
@login_required
def check_reorders():
    conn = get_db()

    products = conn.execute("""
        SELECT * FROM products
        WHERE quantity <= reorder_level
    """).fetchall()

    created = 0

    for product in products:

        existing = conn.execute("""
            SELECT id FROM reorders
            WHERE product_id = ?
            AND status = 'Pending'
        """, (product["id"],)).fetchone()

        if not existing:
            conn.execute("""
                INSERT INTO reorders
                (product_id, quantity, status)
                VALUES (?, ?, 'Pending')
            """, (
                product["id"],
                product["reorder_quantity"]
            ))

            created += 1

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "new_reorders": created
    })


@app.route("/api/reorders/<int:reorder_id>", methods=["PUT"])
@login_required
def update_reorder(reorder_id):
    data = request.get_json() or {}

    status = data.get("status")

    allowed = ["Pending", "Ordered", "Received", "Cancelled"]

    if status not in allowed:
        return jsonify({
            "error": "Invalid reorder status."
        }), 400

    conn = get_db()

    conn.execute(
        "UPDATE reorders SET status = ? WHERE id = ?",
        (status, reorder_id)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Reorder status updated."
    })


# ---------------- DASHBOARD ----------------

@app.route("/api/dashboard", methods=["GET"])
@login_required
def dashboard():
    conn = get_db()

    total_products = conn.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    total_suppliers = conn.execute(
        "SELECT COUNT(*) FROM suppliers"
    ).fetchone()[0]

    low_stock = conn.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE quantity <= reorder_level
    """).fetchone()[0]

    pending_reorders = conn.execute("""
        SELECT COUNT(*)
        FROM reorders
        WHERE status = 'Pending'
    """).fetchone()[0]

    total_stock = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM products"
    ).fetchone()[0]

    conn.close()

    return jsonify({
        "total_products": total_products,
        "total_suppliers": total_suppliers,
        "low_stock": low_stock,
        "pending_reorders": pending_reorders,
        "total_stock": total_stock
    })


# ---------------- REPORTS ----------------

@app.route("/api/reports/stock", methods=["GET"])
@login_required
def stock_report():
    conn = get_db()

    report = conn.execute("""
        SELECT
            product_code,
            name,
            category,
            quantity,
            reorder_level,
            reorder_quantity,
            unit_price,
            CASE
                WHEN quantity <= reorder_level THEN 'LOW STOCK'
                ELSE 'ADEQUATE'
            END AS stock_status
        FROM products
        ORDER BY name
    """).fetchall()

    conn.close()

    return jsonify([dict(row) for row in report])


# ---------------- ADMIN ----------------

@app.route("/api/users", methods=["GET"])
@login_required
def get_users():
    if session.get("role") != "admin":
        return jsonify({"error": "Administrator access required."}), 403

    conn = get_db()

    users = conn.execute("""
        SELECT id, username, role
        FROM users
        ORDER BY id
    """).fetchall()

    conn.close()

    return jsonify([dict(row) for row in users])


@app.route("/api/users", methods=["POST"])
@login_required
def create_user():
    if session.get("role") != "admin":
        return jsonify({"error": "Administrator access required."}), 403

    data = request.get_json() or {}

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    role = data.get("role", "staff")

    if not username or not password:
        return jsonify({
            "error": "Username and password are required."
        }), 400

    if len(password) < 6:
        return jsonify({
            "error": "Password must contain at least 6 characters."
        }), 400

    if role not in ["admin", "user"]:
        return jsonify({
            "error": "Invalid user role."
        }), 400

    conn = get_db()

    try:
        conn.execute("""
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
        """, (
            username,
            generate_password_hash(password),
            role
        ))

        conn.commit()

    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({
            "error": "Username already exists."
        }), 400

    conn.close()

    return jsonify({
        "success": True,
        "message": "User created successfully."
    }), 201


# ---------------- START SERVER ----------------

if __name__ == "__main__":
    init_db()

    print("=" * 50)
    print("LOCAL INVENTORY & AUTOMATED REORDER SYSTEM")
    print("=" * 50)
    print("Database:", DB_FILE)
    print("Open in Chrome: http://127.0.0.1:5000")
    print("Default login: admin / admin123")
    print("=" * 50)

    app.run(debug=True)
