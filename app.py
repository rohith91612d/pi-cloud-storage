from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
import uuid
import mimetypes

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.abspath("storage")
os.makedirs(BASE_DIR, exist_ok=True)

USERS = {}
TOKENS = {}


# ---------------- AUTH ----------------
def get_user():
    token = request.headers.get("Authorization") or request.args.get("token")
    return TOKENS.get(token)


# ---------------- REGISTER ----------------
@app.route("/register", methods=["POST"])
def register():
    data = request.json
    u = data["username"]
    p = data["password"]

    if u in USERS:
        return jsonify({"error": "exists"}), 400

    USERS[u] = p
    os.makedirs(os.path.join(BASE_DIR, u), exist_ok=True)

    return jsonify({"status": "registered"})


# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():
    data = request.json
    u = data["username"]
    p = data["password"]

    if USERS.get(u) == p:
        token = str(uuid.uuid4())
        TOKENS[token] = u
        return jsonify({"token": token})

    return jsonify({"error": "invalid"}), 401


# ---------------- PATH ----------------
def user_path(user, folder):
    folder = folder.strip("/")
    return os.path.join(BASE_DIR, user, folder)


# ---------------- LIST ----------------
@app.route("/list")
def list_files():
    user = get_user()
    if not user:
        return jsonify({"error": "unauth"}), 401

    folder = request.args.get("folder", "")
    path = user_path(user, folder)

    os.makedirs(path, exist_ok=True)

    items = []
    for f in os.listdir(path):
        fp = os.path.join(path, f)
        items.append({
            "name": f,
            "type": "folder" if os.path.isdir(fp) else "file"
        })

    return jsonify({"items": items})


# ---------------- SAFE FILE NAME ----------------
def safe_filename(folder, filename):
    base, ext = os.path.splitext(filename)
    count = 1
    new_name = filename

    while os.path.exists(os.path.join(folder, new_name)):
        new_name = f"{base}({count}){ext}"
        count += 1

    return new_name


# ---------------- UPLOAD ----------------
@app.route("/upload", methods=["POST"])
def upload():
    user = get_user()
    if not user:
        return jsonify({"error": "unauth"}), 401

    folder = request.form.get("folder", "")
    path = user_path(user, folder)

    os.makedirs(path, exist_ok=True)

    file = request.files["file"]
    name = safe_filename(path, file.filename.replace(" ", "_"))

    file.save(os.path.join(path, name))

    return jsonify({"status": "uploaded", "file": name})


# ---------------- DELETE ----------------
@app.route("/delete", methods=["POST"])
def delete():
    user = get_user()
    if not user:
        return jsonify({"error": "unauth"}), 401

    data = request.json
    path = user_path(user, data["path"])

    if os.path.isdir(path):
        os.rmdir(path)
    else:
        os.remove(path)

    return jsonify({"status": "deleted"})


# ---------------- FIXED OPEN FILE ----------------
@app.route("/open")
def open_file():
    user = get_user()
    if not user:
        return jsonify({"error": "unauth"}), 401

    file_path = request.args.get("path")
    path = user_path(user, file_path)

    if not os.path.exists(path):
        return jsonify({"error": "not found"}), 404

    mime, _ = mimetypes.guess_type(path)

    return send_file(path, mimetype=mime, as_attachment=False)


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
