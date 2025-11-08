from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime


app = Flask(__name__)
app.secret_key = "canteen-secret-key"


# ================= DATA STRUCTURES ====================

# Stack implementation using list
class Stack:
    def __init__(self):
        self.stack = []

    def push(self, item):
        self.stack.append(item)

    def pop(self):
        if not self.is_empty():
            return self.stack.pop()
        return None

    def peek(self):
        if not self.is_empty():
            return self.stack[-1]
        return None

    def is_empty(self):
        return len(self.stack) == 0

    def size(self):
        return len(self.stack)


# Node class for Linked List
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None


# Singly Linked List implementation
class LinkedList:
    def __init__(self):
        self.head = None

    def append(self, data):
        new_node = Node(data)
        if not self.head:
            self.head = new_node
            return
        last = self.head
        while last.next:
            last = last.next
        last.next = new_node

    def delete(self, key):
        current = self.head
        prev = None
        while current and current.data["id"] != key:
            prev = current
            current = current.next
        if not current:
            return False
        if prev is None:
            self.head = current.next
        else:
            prev.next = current.next
        return True

    def find(self, key):
        current = self.head
        while current:
            if current.data["id"] == key:
                return current.data
            current = current.next
        return None

    def to_list(self):
        result = []
        current = self.head
        while current:
            result.append(current.data)
            current = current.next
        return result

    def update(self, key, new_data):
        current = self.head
        while current:
            if current.data["id"] == key:
                current.data.update(new_data)
                return True
            current = current.next
        return False

# Queue implemented with LinkedList
class LinkedListQueue:
    def __init__(self, max_size=10):
        self.list = LinkedList()
        self.front = None
        self.rear = None
        self.max_size = max_size

    def enqueue(self, data):
        if len(self.to_list()) >= self.max_size:
            self.dequeue()

        self.list.append(data)
        if not self.front:
            self.front = self.list.head
        current = self.list.head
        while current.next:
            current = current.next
        self.rear = current

    def dequeue(self):
        if self.is_empty():
            return None
        data = self.front.data
        self.front = self.front.next
        self.list.head = self.front
        if not self.front:
            self.rear = None
        return data

    def peek(self):
        if self.is_empty():
            return None
        return self.front.data

    def is_empty(self):
        return self.front is None

    def to_list(self):
        return self.list.to_list()

    def remove_matching(self, match_func):
        prev = None
        current = self.list.head
        while current:
            if match_func(current.data):
                removed_data = current.data
                # Remove node from linked list
                if prev is None:
                    # removing head
                    self.list.head = current.next
                    self.front = self.list.head
                else:
                    prev.next = current.next
                    self.front = self.list.head
                # Update rear
                if self.list.head is None:
                    self.rear = None
                else:
                    cur = self.list.head
                    while cur.next:
                        cur = cur.next
                    self.rear = cur
                return removed_data
            prev = current
            current = current.next
        return None


# ========================= LOGIN =========================
USERNAME = "admin"
PASSWORD = "1234"

next_product_id = 1

products = LinkedList()
transactions = Stack()
transactions_queue = LinkedListQueue(max_size=10)


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["user"] = USERNAME
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# ========================= DASHBOARD =========================
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    total_sales = sum(t["total"] for t in transactions.stack)
    return render_template("dashboard.html", products=products.to_list(), transactions=transactions.stack,
                           total_sales=total_sales)

# ========================= PRODUCTS =========================
@app.route("/products", methods=["GET", "POST"])
def products_page():
    global next_product_id
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form["name"]
        stock = int(request.form["stock"])
        unit = request.form["unit"]
        price = float(request.form["price"])

        new_product = {
            "id": next_product_id,
            "name": name,
            "stock": stock,
            "unit": unit,
            "price": price
        }
        products.append(new_product)
        next_product_id += 1
        return redirect(url_for("products_page"))

    return render_template("products.html", products=products.to_list())


@app.route("/edit_product/<int:pid>", methods=["POST"])
def edit_product(pid):
    if "user" not in session:
        return redirect(url_for("login"))

    new_data = {
        "name": request.form["name"],
        "stock": int(request.form["stock"]),
        "unit": request.form["unit"],
        "price": float(request.form["price"])
    }

    updated = products.update(pid, new_data)
    if not updated:
        return "Product not found", 404

    return redirect(url_for("products_page"))


@app.route("/delete_product/<int:pid>", methods=["POST"])
def delete_product(pid):
    if "user" not in session:
        return redirect(url_for("login"))

    deleted = products.delete(pid)
    if not deleted:
        return "Product not found", 404

    return redirect(url_for("products_page"))

# ========================= TRANSACTIONS =========================
@app.route("/transactions", methods=["GET", "POST"])
def transactions_page():
    if "user" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        product_name = request.form["product_name"]
        quantity = int(request.form["quantity"])
        payment_mode = request.form["payment_mode"]
        reference_number = request.form.get("reference_number", "").strip()

        if payment_mode in ["GCash", "PayMaya"] and not reference_number:
            return "Reference number is required for e-wallet payments.", 400

        product = None
        for p in products.to_list():
            if p["name"] == product_name:
                product = p
                break

        if product:
            if product["stock"] >= quantity:
                total_price = product["price"] * quantity
                product["stock"] -= quantity

                transaction = {
                    "product": product_name,
                    "quantity": quantity,
                    "total": total_price,
                    "payment_mode": payment_mode,
                    "reference_number": reference_number if reference_number else None,
                    "price": product["price"],
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                transactions.push(transaction)
                transactions_queue.enqueue(transaction)
            else:
                return "Not enough stock", 400

    latest_transaction = transactions.peek()

    return render_template(
        "transactions.html",
        transactions=list(reversed(transactions.stack)),
        products=products.to_list(),
        latest=transactions.peek()
    )


@app.route('/undo_last_transaction', methods=['POST'])
def undo_last_transaction():
    if "user" not in session:
        return redirect(url_for("login"))

    if transactions.is_empty():
        return redirect(url_for("transactions_page"))

    last_transaction = transactions.pop()

    current = products.head
    while current:
        if current.data["name"].strip().lower() == last_transaction["product"].strip().lower():
            current.data["stock"] = int(current.data["stock"]) + int(last_transaction["quantity"])
            break
        current = current.next

    prev = None
    current = transactions_queue.list.head
    while current:
        t = current.data
        if (
            t["product"].strip().lower() == last_transaction["product"].strip().lower()
            and int(t["quantity"]) == int(last_transaction["quantity"])
            and float(t["total"]) == float(last_transaction["total"])
        ):
            if prev:
                prev.next = current.next
            else:
                transactions_queue.list.head = current.next
            break
        prev = current
        current = current.next

    return redirect(url_for("transactions_page"))


# ========================= REPORTS =========================
@app.route("/reports")
def reports_page():
    if "user" not in session:
        return redirect(url_for("login"))

    reversed_transactions = list(reversed(transactions_queue.to_list()))

    return render_template(
        "reports.html",
        products=products.to_list(),
        transactions=reversed_transactions
    )


@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))


    user_data = {
        'username': session['user'],
        'email': 'user@example.com',
        'role': 'Admin',
        'joined': '2023-01-15'
    }

    return render_template("profile.html", user=user_data)


# ========================= RUN APP =========================
if __name__ == "__main__":
    app.run(debug=True)