from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import functools

from config import DB_CONFIG, SECRET_KEY
from services import codeforces_api
from services import contest_generator

app = Flask(__name__)
app.secret_key = SECRET_KEY


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def login_required(view_func):
    @functools.wraps(view_func)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    data = request.form
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

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

    return redirect(url_for("login", signup_success=1))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        signup_success = request.args.get("signup_success")
        return render_template("login.html", signup_success=signup_success)

    data = request.form
    username_or_email = data.get("username", "").strip()
    password = data.get("password", "")

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
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (session["user_id"],))
    user = cursor.fetchone()

    cursor.execute(
        "SELECT * FROM contests WHERE owner_user_id = %s ORDER BY created_at DESC",
        (session["user_id"],)
    )
    contests = cursor.fetchall()

    cursor.execute("""
        SELECT ti.*, t.team_name, u.username AS invited_by_username
        FROM team_invites ti
        JOIN teams t ON t.id = ti.team_id
        JOIN users u ON u.id = ti.invited_by_user_id
        WHERE ti.invited_user_id = %s AND ti.status = 'pending'
        ORDER BY ti.created_at DESC
    """, (session["user_id"],))
    pending_invites = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("dashboard.html", user=user, contests=contests, pending_invites=pending_invites)


@app.route("/create-team", methods=["GET", "POST"])
@login_required
def create_team():
    if request.method == "GET":
        return render_template("create_team.html")

    team_name = request.form.get("team_name", "").strip()
    if not team_name:
        return render_template("create_team.html", error="Team name is required.")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO teams (team_name, leader_id) VALUES (%s, %s)",
        (team_name, session["user_id"])
    )
    team_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO team_members (team_id, user_id) VALUES (%s, %s)",
        (team_id, session["user_id"])
    )

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("my_teams"))


@app.route("/my-teams")
@login_required
def my_teams():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE id = %s", (session["user_id"],))
    user = cursor.fetchone()

    cursor.execute("""
        SELECT t.*, (SELECT COUNT(*) FROM team_members tm WHERE tm.team_id = t.id) AS member_count
        FROM teams t
        JOIN team_members tm ON tm.team_id = t.id
        WHERE tm.user_id = %s
        ORDER BY t.created_at DESC
    """, (session["user_id"],))
    teams = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("my_teams.html", user=user, teams=teams)


@app.route("/team/<int:team_id>/invite", methods=["POST"])
@login_required
def invite_to_team(team_id):
    username = request.form.get("username", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM teams WHERE id = %s", (team_id,))
    team = cursor.fetchone()

    if not team or team["leader_id"] != session["user_id"]:
        cursor.close()
        conn.close()
        return redirect(url_for("my_teams"))

    cursor.execute("SELECT COUNT(*) AS cnt FROM team_members WHERE team_id = %s", (team_id,))
    member_count = cursor.fetchone()["cnt"]
    if member_count >= 4:
        cursor.close()
        conn.close()
        return redirect(url_for("my_teams"))

    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    invited_user = cursor.fetchone()

    if invited_user:
        cursor.execute(
            "SELECT * FROM team_invites WHERE team_id = %s AND invited_user_id = %s AND status = 'pending'",
            (team_id, invited_user["id"])
        )
        existing_invite = cursor.fetchone()

        if not existing_invite:
            cursor2 = conn.cursor()
            cursor2.execute(
                "INSERT INTO team_invites (team_id, invited_user_id, invited_by_user_id) VALUES (%s, %s, %s)",
                (team_id, invited_user["id"], session["user_id"])
            )
            conn.commit()
            cursor2.close()

    cursor.close()
    conn.close()

    return redirect(url_for("my_teams"))


@app.route("/invite/<int:invite_id>/accept", methods=["POST"])
@login_required
def accept_invite(invite_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM team_invites WHERE id = %s AND invited_user_id = %s AND status = 'pending'",
        (invite_id, session["user_id"])
    )
    invite = cursor.fetchone()

    if invite:
        cursor.execute("SELECT COUNT(*) AS cnt FROM team_members WHERE team_id = %s", (invite["team_id"],))
        member_count = cursor.fetchone()["cnt"]

        cursor2 = conn.cursor()
        if member_count < 4:
            cursor2.execute(
                "INSERT IGNORE INTO team_members (team_id, user_id) VALUES (%s, %s)",
                (invite["team_id"], session["user_id"])
            )
            cursor2.execute("UPDATE team_invites SET status = 'accepted' WHERE id = %s", (invite_id,))
        conn.commit()
        cursor2.close()

    cursor.close()
    conn.close()

    return redirect(url_for("dashboard"))


@app.route("/invite/<int:invite_id>/reject", methods=["POST"])
@login_required
def reject_invite(invite_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE team_invites SET status = 'rejected' WHERE id = %s AND invited_user_id = %s AND status = 'pending'",
        (invite_id, session["user_id"])
    )
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("dashboard"))


@app.route("/sync-codeforces", methods=["POST"])
@login_required
def sync_codeforces():
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


@app.route("/create-contest", methods=["GET"])
@login_required
def create_contest_page():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (session["user_id"],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template("create_contest.html", user=user)


@app.route("/api/generate-contest", methods=["POST"])
@login_required
def generate_contest():
    payload = request.get_json()

    title = payload.get("title", "").strip() or "Untitled Contest"
    rating_min = int(payload.get("rating_min", 800))
    rating_max = int(payload.get("rating_max", 1200))
    topics = payload.get("topics", [])
    num_questions = int(payload.get("num_questions", 5))

    if num_questions < 5 or num_questions > 7:
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
    solved_rows = cursor.fetchall()
    solved_keys = set(row["problem_key"] for row in solved_rows)

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
        """INSERT INTO contests (title, owner_type, owner_user_id, rating_min, rating_max, topics, num_questions)
           VALUES (%s, 'individual', %s, %s, %s, %s, %s)""",
        (title, session["user_id"], rating_min, rating_max, ",".join(topics), num_questions)
    )
    contest_id = cursor2.lastrowid

    insert_problem_query = """
        INSERT INTO contest_problems
            (contest_id, contest_cf_id, problem_index, problem_name, rating, tags, problem_url, position_in_contest)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    for i, p in enumerate(chosen, start=1):
        url = f"https://codeforces.com/problemset/problem/{p['contestId']}/{p['index']}"
        cursor2.execute(insert_problem_query, (
            contest_id, p["contestId"], p["index"], p["name"], p["rating"],
            ",".join(p.get("tags", [])), url, i
        ))

    conn.commit()
    cursor.close()
    cursor2.close()
    conn.close()

    return jsonify({"success": True, "contest_id": contest_id})


@app.route("/contest/<int:contest_id>")
@login_required
def view_contest(contest_id):
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
