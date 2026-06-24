from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from config import DB_CONFIG, SECRET_KEY
from services import codeforces_api
from services import contest_generator

app = Flask(__name__)
app.secret_key = SECRET_KEY


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not username or not email or not password:
        return render_template("signup.html", error="All fields are required.")

    password_hash = generate_password_hash(password)

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (username, email, password_hash)
        )
        conn.commit()
    except mysql.connector.IntegrityError:
        cursor.close()
        conn.close()
        return render_template("signup.html", error="Username or email already exists.")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username_or_email = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM users WHERE username = %s OR email = %s",
        (username_or_email, username_or_email)
    )
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("dashboard"))

    return render_template("login.html", error="Invalid username/email or password.")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (session["user_id"],))
    user = cursor.fetchone()

    cursor.execute(
        "SELECT * FROM contests WHERE owner_user_id = %s ORDER BY created_at DESC",
        (session["user_id"],)
    )
    contests = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("dashboard.html", user=user, contests=contests)


@app.route("/sync-codeforces", methods=["POST"])
def sync_codeforces():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please login first."})

    handle = request.form.get("handle", "").strip()
    if not handle:
        return jsonify({"success": False, "message": "Please enter a Codeforces handle."})

    try:
        user_info = codeforces_api.fetch_user_info(handle)
        solved = codeforces_api.fetch_user_solved_problems(handle)
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET codeforces_handle = %s, cf_rating = %s, cf_last_synced = %s WHERE id = %s",
        (user_info["handle"], user_info["rating"], datetime.now(), session["user_id"])
    )

    cursor.execute("DELETE FROM solved_problems WHERE user_id = %s", (session["user_id"],))

    insert_query = """
        INSERT INTO solved_problems (user_id, problem_key, contest_id, problem_index, problem_name)
        VALUES (%s, %s, %s, %s, %s)
    """
    rows = [
        (session["user_id"], p["problem_key"], p["contestId"], p["index"], p["name"])
        for p in solved
    ]
    if rows:
        cursor.executemany(insert_query, rows)

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({
        "success": True,
        "message": f"Synced! Handle: {user_info['handle']} (rating: {user_info['rating']}). "
                    f"{len(solved)} solved problems cached."
    })


@app.route("/create-contest")
def create_contest_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (session["user_id"],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("create_contest.html", user=user)


@app.route("/api/generate-contest", methods=["POST"])
def generate_contest():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please login first."})

    payload = request.get_json()
    title = payload.get("title", "").strip() or "Untitled Contest"
    rating_min = int(payload.get("rating_min", 800))
    rating_max = int(payload.get("rating_max", 1200))
    topics = payload.get("topics", [])
    num_questions = int(payload.get("num_questions", 5))
    num_questions = max(5, min(7, num_questions))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE id = %s", (session["user_id"],))
    user = cursor.fetchone()
    if not user["codeforces_handle"]:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": "Please link your Codeforces handle first."})

    cursor.execute("SELECT problem_key FROM solved_problems WHERE user_id = %s", (session["user_id"],))
    solved_keys = set(row["problem_key"] for row in cursor.fetchall())

    try:
        all_problems = codeforces_api.fetch_all_problems()
        chosen = contest_generator.generate_contest_problems(
            all_problems, solved_keys, rating_min, rating_max, topics, num_questions
        )
    except Exception as e:
        cursor.close()
        conn.close()
        return jsonify({"success": False, "message": str(e)})

    cursor2 = conn.cursor()
    cursor2.execute(
        """INSERT INTO contests (title, owner_user_id, rating_min, rating_max, topics, num_questions)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (title, session["user_id"], rating_min, rating_max, ",".join(topics), num_questions)
    )
    contest_id = cursor2.lastrowid

    insert_query = """
        INSERT INTO contest_problems
            (contest_id, contest_cf_id, problem_index, problem_name, rating, tags, problem_url, position_in_contest)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    for i, p in enumerate(chosen, start=1):
        url = f"https://codeforces.com/problemset/problem/{p['contestId']}/{p['index']}"
        cursor2.execute(insert_query, (
            contest_id, p["contestId"], p["index"], p["name"], p["rating"],
            ",".join(p.get("tags", [])), url, i
        ))

    conn.commit()
    cursor.close()
    cursor2.close()
    conn.close()

    return jsonify({"success": True, "contest_id": contest_id})


@app.route("/contest/<int:contest_id>")
def view_contest(contest_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM contests WHERE id = %s", (contest_id,))
    contest = cursor.fetchone()

    if not contest:
        cursor.close()
        conn.close()
        return "Contest not found", 404

    cursor.execute(
        "SELECT * FROM contest_problems WHERE contest_id = %s ORDER BY position_in_contest ASC",
        (contest_id,)
    )
    problems = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("contest_view.html", contest=contest, problems=problems)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
