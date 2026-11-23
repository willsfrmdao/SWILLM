"""Small standard-library web server for the SWILLM swim shop project."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import smtplib
import ssl
import tempfile
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Lock, Thread
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
DATA = ROOT / "data"
CATALOG_FILE = DATA / "products.json"
ORDERS_FILE = DATA / "orders.json"
REGISTRATIONS_FILE = DATA / "class-registrations.json"
HOST = "127.0.0.1"
PORT = 8000
ORDER_EMAIL = "willchisom341@gmail.com"
SMTP_USER = os.environ.get("SWILLM_SMTP_USER", ORDER_EMAIL).strip()
SMTP_PASSWORD = os.environ.get("SWILLM_SMTP_PASSWORD", "").replace(" ", "")
ORDER_LOCK = Lock()
REGISTRATION_LOCK = Lock()
NEW_ORDER = Event()
EMAIL_PATTERN = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")


def load_products() -> list[dict]:
    return json.loads(CATALOG_FILE.read_text(encoding="utf-8"))


def load_records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_records(path: Path, records: list[dict]) -> None:
    file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False)
    temporary = Path(file.name)
    try:
        with file:
            json.dump(records, file, ensure_ascii=False, indent=2)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def send_order_email(order: dict) -> None:
    message = EmailMessage()
    message["From"] = SMTP_USER
    message["To"] = ORDER_EMAIL
    message["Subject"] = f"SWILLM order {order['id']}"
    message["Message-ID"] = f"<{order['id'].lower()}@{SMTP_USER.split('@')[-1]}>"
    customer = order["customer"]
    items = [
        f"{line['quantity']} × {line['name']} ({line['size']}, {line['color']}) — ₦{line['lineTotal']:,}"
        for line in order["items"]
    ]
    message.set_content("\n".join([
        f"New SWILLM demo order {order['id']}",
        f"Placed: {order['createdAt']}",
        f"Customer: {customer['name']}",
        f"Email: {customer['email']}",
        "",
        *items,
        "",
        f"Items subtotal: ₦{order['total']:,}",
        "Payment: none collected",
    ]))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15, context=ssl.create_default_context()) as smtp:
        smtp.login(SMTP_USER, SMTP_PASSWORD)
        smtp.send_message(message)


def deliver_order_emails() -> None:
    while True:
        NEW_ORDER.clear()
        try:
            with ORDER_LOCK:
                pending = [order for order in reversed(load_records(ORDERS_FILE)) if order.get("notificationStatus") == "pending"]
            for order in pending:
                send_order_email(order)
                with ORDER_LOCK:
                    orders = load_records(ORDERS_FILE)
                    saved = next(item for item in orders if item["id"] == order["id"])
                    saved["notificationStatus"] = "sent"
                    save_records(ORDERS_FILE, orders)
        except (OSError, ValueError) as error:
            print(f"Order email delivery will retry in 60 seconds ({type(error).__name__}).", flush=True)
            Event().wait(60)
            continue
        NEW_ORDER.wait(60)


def public_order(order: dict) -> dict:
    return {key: value for key, value in order.items() if key not in {"requestId", "requestHash", "notificationStatus"}}


class ShopHandler(BaseHTTPRequestHandler):
    server_version = "SWILLM/1.0"

    def send_json(self, payload: object, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if path == "/api/health":
            return self.send_json({"status": "ok", "shop": "SWILLM"})
        if path == "/api/products":
            return self.send_json(load_products())
        if path == "/api/orders":
            with ORDER_LOCK:
                orders = load_records(ORDERS_FILE)
            return self.send_json([{**public_order(order), "notificationStatus": order.get("notificationStatus", "not queued")} for order in orders])
        if path == "/api/class-registrations":
            with REGISTRATION_LOCK:
                registrations = load_records(REGISTRATIONS_FILE)
            return self.send_json([{key: value for key, value in entry.items() if key != "requestId"} for entry in registrations])
        if path in {"/", "/index.html"}:
            file_path = ROOT / "index.html"
        else:
            file_path = (PUBLIC / path.lstrip("/")).resolve()
            if not file_path.is_relative_to(PUBLIC.resolve()):
                return self.send_error(404, "Page not found")
        if not file_path.is_file():
            return self.send_error(404, "Page not found")
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path not in {"/api/orders", "/api/class-registrations"}:
            return self.send_error(404, "Route not found")
        submission = "registration" if path == "/api/class-registrations" else "order"
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 32_000:
                return self.send_json({"error": f"{submission.capitalize()} is too large."}, 413)
            if length < 1:
                raise ValueError("Request body is empty")
            incoming = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(incoming, dict):
                raise ValueError("Invalid request")
            if path == "/api/class-registrations":
                return self.register_for_classes(incoming)
            customer = incoming.get("customer", {})
            items = incoming.get("items", [])
            if not isinstance(customer, dict) or not isinstance(items, list) or not items:
                return self.send_json({"error": "Add your name, email and at least one item."}, 400)
            name = customer.get("name", "")
            email = customer.get("email", "")
            if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
                return self.send_json({"error": "Enter your full name."}, 400)
            if not isinstance(email, str) or len(email.strip()) > 160 or not EMAIL_PATTERN.fullmatch(email.strip()):
                return self.send_json({"error": "Enter a valid email address."}, 400)
            request_id = incoming.get("requestId")
            request_hash = None
            if request_id is not None:
                if not isinstance(request_id, str) or str(uuid.UUID(request_id)) != request_id:
                    raise ValueError("Invalid order request ID")
                request_hash = hashlib.sha256(json.dumps([customer, items], sort_keys=True).encode()).hexdigest()

            catalog = {item["id"]: item for item in load_products()}
            order_items = []
            total = 0
            for requested in items:
                if not isinstance(requested, dict):
                    raise ValueError("Invalid order item")
                product = catalog.get(requested.get("productId"))
                quantity = requested.get("quantity", 0)
                if not product or type(quantity) is not int or not 1 <= quantity <= 20:
                    return self.send_json({"error": "One of the selected items is invalid."}, 400)
                size = requested.get("size", product["sizes"][0])
                color = requested.get("color", product["color"])
                if size not in product["sizes"] or color not in product.get("colors", [product["color"]]):
                    return self.send_json({"error": "One of the selected sizes or colors is unavailable."}, 400)
                line_total = product["price"] * quantity
                total += line_total
                order_items.append({
                    "productId": product["id"],
                    "name": product["name"],
                    "quantity": quantity,
                    "size": size,
                    "color": color,
                    "unitPrice": product["price"],
                    "lineTotal": line_total,
                })

            order = {
                "id": f"SW-{uuid.uuid4().hex[:8].upper()}",
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "customer": {
                    "name": name.strip(),
                    "email": email.strip(),
                    "phone": str(customer.get("phone", ""))[:40],
                    "address": str(customer.get("address", ""))[:240],
                },
                "items": order_items,
                "total": total,
                "currency": "NGN",
                "paymentStatus": "demo — not charged",
                "status": "received",
                "notificationStatus": "pending",
            }
            with ORDER_LOCK:
                orders = load_records(ORDERS_FILE)
                existing = next((item for item in orders if item.get("requestId") == request_id), None) if request_id else None
                if existing is None:
                    if request_id:
                        order.update(requestId=request_id, requestHash=request_hash)
                    orders.insert(0, order)
                    save_records(ORDERS_FILE, orders)
            if existing is not None:
                if existing["requestHash"] != request_hash:
                    return self.send_json({"error": "This order reference has already been used."}, 409)
                return self.send_json(public_order(existing))
            NEW_ORDER.set()
            return self.send_json(public_order(order), 201)
        except (ValueError, TypeError, KeyError):
            return self.send_json({"error": f"Please check the {submission} details and try again."}, 400)
        except OSError as error:
            self.log_error("Could not save a %s (%s)", submission, type(error).__name__)
            return self.send_json({"error": f"Could not save your {submission}. Please try again."}, 503)

    def register_for_classes(self, incoming: dict) -> None:
        months = incoming.get("months")
        if type(months) is not int or months not in {1, 2, 6}:
            return self.send_json({"error": "Choose a 1-, 2- or 6-month programme."}, 400)
        teacher = incoming.get("teacherPreference")
        if teacher not in ("male", "female"):
            return self.send_json({"error": "Choose a male or female teacher."}, 400)
        name = incoming.get("name")
        if not isinstance(name, str) or not name.strip() or len(name.strip()) > 100:
            return self.send_json({"error": "Enter the swimmer’s full name."}, 400)
        email = incoming.get("email")
        if not isinstance(email, str) or len(email.strip()) > 160 or not EMAIL_PATTERN.fullmatch(email.strip()):
            return self.send_json({"error": "Enter a valid contact email address."}, 400)
        request_id = incoming.get("requestId")
        if request_id is not None and (not isinstance(request_id, str) or str(uuid.UUID(request_id)) != request_id):
            raise ValueError("Invalid registration request ID")

        details = {"name": name.strip(), "email": email.strip(), "months": months, "teacherPreference": teacher}
        with REGISTRATION_LOCK:
            registrations = load_records(REGISTRATIONS_FILE)
            existing = next((entry for entry in registrations if entry.get("requestId") == request_id), None) if request_id else None
            if existing is None:
                registration = {
                    **details,
                    "id": f"CL-{uuid.uuid4().hex[:8].upper()}",
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "requestId": request_id,
                    "status": "Pending confirmation",
                }
                registrations.insert(0, registration)
                save_records(REGISTRATIONS_FILE, registrations)
        if existing is not None:
            if any(existing[key] != value for key, value in details.items()):
                return self.send_json({"error": "This registration reference has already been used."}, 409)
            return self.send_json({"id": existing["id"]})
        return self.send_json({"id": registration["id"]}, 201)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {format % args}")


if __name__ == "__main__":
    DATA.mkdir(exist_ok=True)
    if SMTP_USER and SMTP_PASSWORD:
        Thread(target=deliver_order_emails, daemon=True, name="order-email").start()
    else:
        print("Order emails will queue until SWILLM_SMTP_PASSWORD is configured.", flush=True)
    print(f"SWILLM is running at http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), ShopHandler).serve_forever()
