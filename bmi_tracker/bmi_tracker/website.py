from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import csv
import hashlib
import hmac
import os
from datetime import datetime, date
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# the web server doesn't run from this folder, so build paths from where this file lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# files to save data
DATA_FILE = os.path.join(BASE_DIR, "user_data.csv")
USERS_FILE = os.path.join(BASE_DIR, "users.csv")

# os.urandom on every start logs everyone out whenever the server restarts,
# so use an env var if it's set, otherwise make one once and keep it in a file
def load_secret_key():
    key = os.environ.get("SECRET_KEY")
    if key:
        return key
    key_file = os.path.join(BASE_DIR, "secret_key.txt")
    if not os.path.exists(key_file):
        fd = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(os.urandom(32).hex())
    with open(key_file) as f:
        return f.read().strip()


web = Flask(__name__)
web.secret_key = load_secret_key()
web.config["SESSION_PERMANENT"] = False
web.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# creates user data file
def user_data_file():
    if not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0:
        with open(DATA_FILE, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Username", "FullName", "Date", "Height(ft)", "Height(in)", "TotalHeight(in)", "Weight(lb)", "BMI", "Category",])
# creates user fileS
def users_file():
    if not os.path.exists(USERS_FILE) or os.path.getsize(USERS_FILE) == 0:
        with open(USERS_FILE, mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Username", "FullName", "Birthday", "PasswordHash", "SecurityQuestion", "SecurityAnswer"])

# classifies bmi under 4 categories
def classify_bmi(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal weight"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"

# make sure height and weight input are in the correct format
def validate_bmi_input(feet, inches, weight_lb):
    try:
        feet = int(feet)
        inches = int(inches)
        weight_lb = float(weight_lb)
    except ValueError:
        return False, "Height must be whole numbers, weight must be a number.", None, None, None
    if feet <= 0:
        return False, "Feet must be greater than zero.", None, None, None
    if inches < 0:
        return False, "Inches cant be negative.", None, None, None
    if inches >= 12:
        return False, "Inches must be less than 12.", None, None, None
    if weight_lb <= 0:
        return False, "Weight must be greater than zero.", None, None, None
    return True, "", feet, inches, weight_lb

# add user data to the data file
def load_data():
    rows = []
    if not os.path.exists(DATA_FILE):
        return rows
    with open(DATA_FILE, mode="r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["Height(ft)"] = int(row["Height(ft)"])
            row["Height(in)"] = int(row["Height(in)"])
            row["TotalHeight(in)"] = int(row["TotalHeight(in)"])
            row["Weight(lb)"] = float(row["Weight(lb)"])
            row["BMI"] = float(row["BMI"])
            rows.append(row)
    return rows

# update bmi if user updates weight input because only one bmi per day is allowed
def update_bmi(username, entry_date, feet, inches, total_height_in, weight_lb, bmi, category):
    rows = []
    with open(DATA_FILE, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["Username"].strip().lower() == username.strip().lower() and row["Date"] == entry_date:
                row["Height(ft)"] = feet
                row["Height(in)"] = inches
                row["TotalHeight(in)"] = total_height_in
                row["Weight(lb)"] = weight_lb
                row["BMI"] = bmi
                row["Category"] = category
            rows.append(row)
    with open(DATA_FILE, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

# calculate bmi then save weight, height, ad bmi to csv file  
def save_entry(username, full_name, feet, inches, weight_lb, entry_date=None):
    user_data_file()
    is_valid, message, clean_ft, clean_inch, clean_weight = validate_bmi_input(feet, inches, weight_lb)
    if not is_valid:
        return {"success": False, "message": message}
    if entry_date is None:
        entry_date = datetime.now().strftime("%Y-%m-%d")
    total_height_in = (clean_ft * 12) + clean_inch
    bmi = round((clean_weight * 703) / (total_height_in ** 2), 2)
    category = classify_bmi(bmi)
    data = load_data()
    entry_updated = False
    for row in data:
        if row["Username"].strip().lower() == username.strip().lower() and row["Date"] == entry_date:
            update_bmi(username, entry_date, clean_ft, clean_inch, total_height_in, clean_weight, bmi, category)
            entry_updated = True
            break
    if not entry_updated:
        with open(DATA_FILE, mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([username, full_name, entry_date, clean_ft, clean_inch, total_height_in, clean_weight, bmi, category])
    return {
        "success": True,
        "message": "Updated Successfully." if entry_updated else "Saved Successfully.",
        "username": username,
        "fullname": full_name,
        "date": entry_date,
        "height_ft": clean_ft,
        "height_in": clean_inch,
        "weight_lb": clean_weight,
        "bmi": bmi,
        "category": category
    }

# count how many users and entries there are and the bmi ranges
def get_statistics():
    data = load_data()
    category_counts = {"Underweight": 0, "Normal weight": 0, "Overweight": 0, "Obese": 0}
    if not data:
        return {"total_entries": 0, "total_users": 0, "average_bmi": 0, "category_counts": category_counts}
    bmi_values = [row["BMI"] for row in data]
    unique_users = set(row["Username"] for row in data)
    for row in data:
        category = row["Category"].strip()
        if category in category_counts:
            category_counts[category] += 1
    return {
        "total_entries": len(data),
        "total_users": len(unique_users),
        "average_bmi": round(sum(bmi_values) / len(bmi_values), 2),
        "category_counts": category_counts
    }

# bmi range chart in the stats page
def category_chart():
    stats = get_statistics()
    categories = list(stats["category_counts"].keys())
    counts = list(stats["category_counts"].values())
    os.makedirs(web.static_folder, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("#ece4da")
    ax.set_facecolor("#f7f3ee")
    bars = ax.bar(categories, counts, color="#8a5a4a", edgecolor="#6f4639", linewidth=1.2)
    ax.set_title("BMI Classification Distribution", fontsize=18, color="#6f4639", pad=14)
    ax.set_xlabel("Classification", fontsize=12, color="#5a463d")
    ax.set_ylabel("Count", fontsize=12, color="#5a463d")
    ax.tick_params(axis="x", colors="#5a463d", labelsize=12)
    ax.tick_params(axis="y", colors="#5a463d", labelsize=12)
    for spine in ax.spines.values():
        spine.set_color("#d8c8bb")
    ax.grid(axis="y", linestyle="--", alpha=0.25, color="#b89f90")
    ax.set_axisbelow(True)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height + 0.03, f"{int(height)}", ha="center", va="bottom", fontsize=11, color="#6f4639")
    plt.tight_layout()
    plt.savefig(os.path.join(web.static_folder, "category_chart.png"), facecolor=fig.get_facecolor())
    plt.close()

# every user gets their own chart file, otherwise two people viewing
# the progress page at the same time could end up seeing each other's chart
def chart_filename(username):
    digest = hmac.new(web.secret_key.encode(), username.strip().lower().encode(), hashlib.sha256).hexdigest()[:20]
    return f"trend_{digest}.png"

# user progress chart to add in the my progress page
def user_trend_chart(username, full_name):
    data = load_data()
    user_entries = []
    for row in data:
        if row["Username"].strip().lower() == username.strip().lower():
            user_entries.append(row)
    if not user_entries:
        return False
    user_entries.sort(key=lambda row: row["Date"])
    dates = [row["Date"] for row in user_entries]
    bmis = [row["BMI"] for row in user_entries]
    os.makedirs(web.static_folder, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("#ece4da")
    ax.set_facecolor("#f7f3ee")
    ax.plot(dates, bmis, marker="o", markersize=8, linewidth=2.5, color="#8a5a4a", markerfacecolor="#8a5a4a", markeredgecolor="#6f4639")
    ax.set_title(f"BMI Trend for {full_name}", fontsize=18, color="#6f4639", pad=14)
    ax.set_xlabel("Date", fontsize=12, color="#5a463d")
    ax.set_ylabel("BMI", fontsize=12, color="#5a463d")
    ax.tick_params(axis="x", colors="#5a463d", labelsize=11, rotation=35)
    ax.tick_params(axis="y", colors="#5a463d", labelsize=11)
    for spine in ax.spines.values():
        spine.set_color("#d8c8bb")
    ax.grid(True, linestyle="--", alpha=0.22, color="#b89f90")
    ax.set_axisbelow(True)
    plt.tight_layout()
    plt.savefig(os.path.join(web.static_folder, chart_filename(username)), facecolor=fig.get_facecolor())
    plt.close()
    return True

# check if user exists
def username_exists(username):
    if not os.path.exists(USERS_FILE):
        return False
    with open(USERS_FILE, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["Username"].strip().lower() == username.strip().lower():
                return True
    return False

# create a new user account
def create_account(username, full_name, birthday, password, security_q, security_a):
    users_file()
    password_hash = generate_password_hash(password)
    with open(USERS_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([username.strip(), full_name.strip(), birthday.strip(), password_hash, security_q.strip(), security_a.strip().lower()])

# authenticate exisiting user
def authenticate_login(username, password):
    if not os.path.exists(USERS_FILE):
        return False
    with open(USERS_FILE, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["Username"].strip().lower() == username.strip().lower():
                return check_password_hash(row["PasswordHash"], password)
    return False

# find the username to check if account exists
def find_username(username):
    if not os.path.exists(USERS_FILE):
        return None
    with open(USERS_FILE, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["Username"].strip().lower() == username.strip().lower():
                return row
    return None

# if password forgotten it this will get the security question the user choose
def get_sec_question(username):
    user = find_username(username)
    if user:
        return user["SecurityQuestion"]
    return None
 
# verify security answer to question so that user can change their password
def verify_sec_answer(username, security_a):
    user = find_username(username)
    if user:
        return user["SecurityAnswer"].strip().lower() == security_a.strip().lower()
    return False

# reset password if password is forgotten
def reset_password(username, new_password):
    rows = []
    with open(USERS_FILE, mode="r", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        for row in reader:
            if row["Username"].strip().lower() == username.strip().lower():
                row["PasswordHash"] = generate_password_hash(new_password)
            rows.append(row)
    with open(USERS_FILE, mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

# checks if user is logged in and clear the session is user deleted their account
def logged_in():
    if "username" not in session:
        return False
    user = find_username(session["username"])
    if user is None:
        session.pop("username", None)
        session.pop("full_name", None)
        return False
    return True

# caculates the age of the users (should be more than 13)
def calculate_age(birthday_str):
    birth_day = datetime.strptime(birthday_str, "%Y-%m-%d").date()
    today = date.today()
    age = today.year - birth_day.year
    if (today.month, today.day) < (birth_day.month, birth_day.day): age -= 1
    return age, birth_day

# route to main page
@web.route("/")
def home():
    return render_template("main.html", logged_in=logged_in(), username=session.get("username"), full_name=session.get("full_name"))

# route to signup page
@web.route("/signup", methods=["GET", "POST"])
def signup():
    message = None
    security_questions = ["What is your favorite color?", "What city were you born in?", "What was the name of your first pet?", "What is your mother's maiden name?"]
    if request.method == "POST":
        full_name = request.form.get("fullname", "").strip()
        username = request.form.get("username", "").strip()
        birthday = request.form.get("birthday", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        security_q = request.form.get("security_q", "").strip()
        security_a = request.form.get("security_a", "").strip()
        if not full_name:
            message = "Full name can't be empty."
        elif not username:
            message = "Username can't be empty."
        elif not birthday:
            message = "Birthday is required."
        else:
            try:
                age, birth_date = calculate_age(birthday)
                if birth_date > date.today():
                    message = "Birthday can't be in the future."
                elif age < 13:
                    message = "You must be at least 13 years old to sign up."
                elif age > 120:
                    message = "Please enter a valid birthday."
            except ValueError:
                message = "Please enter a valid birthday."
        if message is None:
            if not password:
                message = "Password can't be empty."
            elif password != confirm_password:
                message = "Passwords don't match."
            elif not security_q:
                message = "Choose a security question."
            elif not security_a:
                message = "Type an answer."
            elif username_exists(username):
                message = "Try again, the username is already taken."
            else:
                create_account(username, full_name, birthday, password, security_q, security_a)
                return redirect(url_for("login", signup="success"))
    return render_template("signup.html", message=message, security_questions=security_questions)

# route to login page
@web.route("/login", methods=["GET", "POST"])
def login():
    message = None
    if request.args.get("reset") == "success":
        message = "Password updated. Log in."
    if request.args.get("signup") == "success":
        message = "Account created. Log in."
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        user = find_username(username)
        if not user:
            message = "No account was found sign up."
        elif authenticate_login(username, password):
            session.permanent = False
            session["username"] = user["Username"]
            session["full_name"] = user["FullName"]
            return redirect(url_for("home"))
        else:
            message = "Incorrect password."
    return render_template("login.html", message=message)

# route to forgot password page
@web.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    message = None
    security_q = None
    username = ""
    step = 1
    if request.method == "POST":
        step = request.form.get("step", "1")
        username = request.form.get("username", "").strip()
        if step == "1":
            if not username_exists(username):
                message = "No account was found with that username."
                step = 1
            else:
                security_q = get_sec_question(username)
                step = 2
        elif step == "2":
            security_a = request.form.get("security_a", "").strip()
            new_password = request.form.get("new_password", "").strip()
            confirm_password = request.form.get("confirm_password", "").strip()
            if not username_exists(username):
                message = "No account was found with that username."
                step = 1
            else:
                security_q = get_sec_question(username)
                if not security_a:
                    message = "Enter the security answer."
                elif not new_password:
                    message = "Enter a new password."
                elif new_password != confirm_password:
                    message = "Passwords don't match."
                elif not verify_sec_answer(username, security_a):
                    message = "Security answer is incorrect."
                else:
                    user = find_username(username)
                    if check_password_hash(user["PasswordHash"], new_password):
                        message = "Your new password should be different than your old one."
                    else:
                        reset_password(username, new_password)
                        return redirect(url_for("login", reset="success"))
                step = 2
        else:
            step = 1
    return render_template("forgotpassword.html", message=message, security_q=security_q, username=username, step=step)

# route to logout page
@web.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("full_name", None)
    return redirect(url_for("home"))

# route to bmi clac page
@web.route("/calculator", methods=["GET", "POST"])
def calculator():
    if not logged_in():
        return redirect(url_for("login"))
    result = None
    if request.method == "POST":
        height_ft = request.form.get("height_ft", "")
        height_in = request.form.get("height_in", "")
        weight_lb = request.form.get("weight_lb", "")
        result = save_entry(session["username"], session["full_name"], height_ft, height_in, weight_lb)
    return render_template("calculator.html", result=result, username=session.get("username"), full_name=session.get("full_name"))

# route to stats page
@web.route("/stats")
def stats():
    if not logged_in():
        return redirect(url_for("login"))
    stats_data = get_statistics()
    category_chart()
    return render_template("stats.html", stats=stats_data, username=session.get("username"), full_name=session.get("full_name"))

# route to user progress page
@web.route("/progress")
def progress():
    if not logged_in():
        return redirect(url_for("login"))
    user_chart_exists = user_trend_chart(session["username"], session["full_name"])
    return render_template("progress.html", user_chart_exists=user_chart_exists, chart_file=chart_filename(session["username"]), username=session.get("username"), full_name=session.get("full_name"))

# make sure the csv files exist even when the server imports this file instead of running it
user_data_file()
users_file()

if __name__ == "__main__":
    # only for running on your own computer, the web host never gets here
    web.run(debug=True)