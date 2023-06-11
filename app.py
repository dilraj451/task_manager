import os
from pathlib import Path
from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, send_from_directory, url_for
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from extra import login_required, get_msgs, view_task, date_formatter, category, task_table, collab_processor, access_check, task_del
from datetime import datetime


# Configure application and parameters for uploaded files
app = Flask(__name__)
app.config['UPLOAD_DIRECTORY'] = str(Path.cwd()) + '/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # Sets max file size (16 GB)
app.config['ALLOWED_EXTENSIONS'] = ['.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.doc', '.docx', '.pptx', '.xlsx']

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure database
db = SQL("sqlite:///project.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Homepage
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Display upcoming deadlines"""

    # Outputs all due tasks that are uncompleted
    if request.method == "GET":
        return task_table(db, "complete = 'NO' AND deadline >= CURRENT_TIMESTAMP", "index.html", session["user_id"])

    else:

        # User submits tasks that have been completed
        completed_ids = request.form.getlist("comp_tasks[]")

        # Updates database and reloads homepage
        if completed_ids:
            for id in completed_ids:
                db.execute("UPDATE tasks SET complete = 'YES' WHERE id = ?", id)
        return redirect("/")


@app.route("/update/<completed_id>", methods=["POST"])
@login_required
def update(completed_id):

    """Marks task as complete"""

    db.execute("UPDATE tasks SET complete = 'YES' WHERE id = ?", completed_id)
    return redirect("/")


@app.route("/update_undo/<completed_id>", methods=["POST"])
@login_required
def update_undo(completed_id):

    """Marks completed task as uncomplete"""

    db.execute("UPDATE tasks SET complete = 'NO' WHERE id = ?", completed_id)
    return redirect(url_for('completed'))


@app.route("/create", methods=["GET", "POST"])
@login_required
def create():

    """Create new event"""

    if request.method == "POST":

        # Stores user input in form
        task = request.form.get("task")
        participants = request.form.getlist("persons[]")
        deadline = request.form.get("deadline")

        # Verifies task name input and is not duplicate
        if not task:
            return render_template("create.html", err_code="task name missing")
        task_check = db.execute("SELECT id FROM tasks WHERE task = ?", task)
        if task_check:
            return render_template("create.html", err_code="task already exists")

        # Verifies deadline input and valid
        if not deadline:
            return render_template("create.html", err_code="deadline missing")
        deadline = date_formatter(deadline)
        if deadline <= datetime.now():
            return render_template("create.html", err_code="invalid deadline")

        # Creates new database entry and retrieves corresponding id
        db.execute("INSERT INTO tasks (creator_id, task, deadline) values (?, ?, ?)",
                   session["user_id"], task, deadline)
        task_id = db.execute("SELECT id FROM tasks WHERE creator_id = ? AND task = ? AND deadline = ?",
                             session["user_id"], task, deadline)[0]["id"]

        # Submits collaborator names to database then returns to homepage
        if participants:
            temp = collab_processor(db, participants, task_id, "INSERT")
            if temp[0] == False:
                db.execute("DELETE FROM tasks WHERE id = ?", task_id)
                return render_template("create.html", err_code=temp[1]+temp[2])

        # Creates new directory for files uploaded by users for task
        uploads_path = os.path.join(app.config['UPLOAD_DIRECTORY'], str(task_id))
        os.mkdir(uploads_path)

        return redirect("/")

    # GET methods renders relevant html page
    else:
        return render_template("create.html")


@app.route("/completed")
@login_required
def completed():

    """Displays completed tasks"""

    return task_table(db, "complete = 'YES'", "completed.html", session["user_id"])


@app.route("/overdue")
@login_required
def overdue():

    """Displays expired tasks"""

    return task_table(db, "complete = 'NO' AND deadline < CURRENT_TIMESTAMP", "overdue.html", session["user_id"])


@app.route("/login", methods=["GET", "POST"])
def login():

    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            return render_template("login.html", err_code="username missing")

        # Ensure password was submitted
        if not password:
            return render_template("login.html", err_code="password missing")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return render_template("login.html", err_code="invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # GET method returns html page
    else:
        return render_template("login.html")




@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():

    """Register user"""

    session.clear()

    if request.method == "POST":

        # Stores user input
        name = request.form.get("name")
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            return render_template("register.html", err_code="username missing")

        # Ensure name submitted
        if not name:
            return render_template("register.html", err_code="name missing")

        # Ensure password was submitted
        if not password or not confirmation:
            return render_template("register.html", err_code="password missing")

        # Check passwords match
        if password != confirmation:
            return render_template("register.html", err_code="passwords do not match")

        # Check password meets requirements
        uppercase = False
        lowercase = False
        numeric = False
        for i in range(len(password)):
            if password[i].isupper() == True:
                uppercase = True
            elif password[i].islower() == True:
                lowercase = True
            elif password[i].isdigit() == True:
                numeric = True

        if len(password) < 8 or uppercase == False or lowercase == False or numeric == False:
            return render_template("register.html",
                                   err_code="password must contain minimum 8 characters including one uppercase letter, lowercase letter, and a digit")

        # Check username/name not taken
        check_names = db.execute("SELECT name, username FROM users")
        for check_name in check_names:
            if username == check_name["username"]:
                return render_template("register.html", err_code="username already allocated")
            elif name == check_name["name"]:
                return render_template("register.html", err_code=name+" already exists. Use your full name.")

        # Creates database entry for new user then goes to login page
        db.execute("INSERT INTO users (name, username, hash) VALUES (?, ?, ?)", name, username, generate_password_hash(password))
        return redirect("\login")

    # GET method
    else:
        return render_template("register.html")


@app.route("/view/<task_id>")
@login_required
def view(task_id):

    """View Task Details"""

    # Checks user is allowed access to task details
    access = access_check(db, session["user_id"], task_id, 'VIEW')
    if access == False:
        return redirect("/")

    # Case that access is allowed
    else:

        # Retrieves task details and messages
        task_overview = view_task(db, task_id)
        task_msgs = get_msgs(db, session["user_id"], task_id)

        if not task_msgs:
            task_msgs = 0

        # Determines if user is administrator
        admin_id = db.execute("SELECT creator_id FROM tasks WHERE id = ?", task_id)[0]["creator_id"]
        admin = False
        if session["user_id"] == admin_id:
            admin = True

        # Determines if page can be edited (i.e. completed or not)
        page = category(db, task_id)
        editable = True
        if page == "completed":
            editable = False

        # Retrives files uploaded in task folder
        files = os.listdir(os.path.join(app.config['UPLOAD_DIRECTORY'], str(task_id)))

        if not files:
            meta_data = 0

        else:
            meta_data = []
            for file in files:
                task_files = db.execute("SELECT filename, id FROM files WHERE task_id = ?", task_id)
                for task_file in task_files:
                    if file == task_file["filename"]:
                        # File meta data recorded
                        meta_data.append(db.execute("SELECT filename, uploader, date FROM files WHERE id = ?",
                                                    task_file["id"])[0])
                        index = len(meta_data) - 1

                        # Uploader and date created details processed for html output
                        meta_data[index]["date"] = datetime.strptime(meta_data[index]["date"],
                                                                     '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%y %H:%M')
                        meta_data[index]["uploader"] = db.execute("SELECT name FROM users WHERE id = ?",
                                                                            meta_data[index]["uploader"])[0]["name"]
                        break


        # Ouputs html page with all processed data afore
        return render_template("view.html", data=task_overview, msgs=task_msgs,
                               admin=admin, editable=editable, meta=meta_data, user_id=session["user_id"])



@app.route("/send_message/<task_id>", methods=["POST"])
@login_required
def send_message(task_id):

    """Send messages"""

    # Records input message into database
    new_msg = request.form.get("new_message")
    if new_msg:
        db.execute("INSERT INTO messages (sender_id, task_id, content, date) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
                   session["user_id"], task_id, new_msg)

    # Refreshes html page
    return redirect(url_for('view', task_id=task_id))


@app.route("/edit_details/<task_id>", methods=["GET", "POST"])
@login_required
def edit_details(task_id):

    """Edit exisiting task details"""

    if request.method == "GET":

        # Check user has access to edit task details
        access = access_check(db, session["user_id"], task_id, 'EDIT')
        if access == False:
            return redirect("/")

        # Access verified
        else:
            # Html edit page loaded with current task details
            task_details = view_task(db, task_id)
            return render_template("edit.html", current=task_details)

    else:

        # Stores user input
        new_task = request.form.get("new_task")
        new_deadline = request.form.get("new_deadline")
        new_collabs = request.form.getlist("new_persons[]")
        remove_collabs = request.form.getlist("del_collabs[]")

        # Current task data
        current_task = view_task(db, task_id)

        # Updates task name if present and valid
        if new_task:
            check_duplicate = db.execute("SELECT id FROM tasks WHERE task = ?", new_task)
            if check_duplicate and check_duplicate[0]["id"] != task_id:
                return render_template("edit.html", current=current_task, err_code="task already exists")
            db.execute("UPDATE tasks SET task = ? WHERE id = ?", new_task, task_id)
            current_task = view_task(db, task_id)

        # Updates deadline if present and valid
        if new_deadline:
            new_deadline = date_formatter(new_deadline)
            if new_deadline <= datetime.now():
                return render_template("edit.html", current=current_task, err_code="invalid deadline selected")
            db.execute("UPDATE tasks SET deadline = ? WHERE id = ?", new_deadline, task_id)
            current_task = view_task(db, task_id)

        # Updates collaborators
        if remove_collabs:
            temp1 = collab_processor(db, remove_collabs, task_id, "DELETE")
            if temp1[0] == False:
                return render_template("edit.html", current=current_task, err_code=temp1[1]+temp1[2])
            current_task = view_task(db, task_id)

        if new_collabs:
            temp2 = collab_processor(db, new_collabs, task_id, "INSERT")
            if temp2[0] == False:
                return render_template("edit.html", current=current_task, err_code=temp2[1]+temp2[2])

        # Returns to task viewer page
        return redirect(url_for('view', task_id=task_id))





@app.route("/delete_task/<task_id>")
@login_required
def delete_task(task_id):

    """Delete selected task"""

    # Determine correct route post-deletion
    task_type = category(db, task_id)
    if task_type == "completed":
        destination = 'completed'
    elif task_type == "overdue":
        destination = 'overdue'
    else:
        destination = 'index'

    # Deletes files in task's directory
    files = db.execute("SELECT filename FROM files WHERE task_id = ?", task_id)
    for file in files:
        os.remove(os.path.join(os.path.join(app.config['UPLOAD_DIRECTORY'], str(task_id)), file["filename"]))

    # Delete data from database
    task_del(db, task_id)

    # Deletes task's directory from filespace
    os.rmdir(os.path.join(app.config['UPLOAD_DIRECTORY'], str(task_id)))

    return redirect(url_for(destination))


@app.route("/back/<task_id>")
@login_required
def back(task_id):

    """Return to relevant page"""

    # Obtain task category
    task_type = category(db, task_id)

    # Determine valid route and execute
    if task_type == "completed":
        return redirect("/completed")
    elif task_type == "overdue":
        return redirect("/overdue")
    else:
        return redirect("/")


@app.route("/upload/<task_id>", methods=["POST"])
def upload(task_id):

    """Uploads user's file to relevant task directory"""

    try:
        # Store file and filetype
        file = request.files["file"]
        extension = os.path.splitext(file.filename)[1].lower()

        if file:
            # Checks filetype is valid
            if extension not in app.config['ALLOWED_EXTENSIONS']:
                return "Invalid file type"

            # If new file is a duplicate, previous database entry deleted before new entry
            duplicate = db.execute("SELECT id FROM files WHERE task_id = ? AND filename = ?",
                                    task_id, secure_filename(file.filename))
            if duplicate:
                db.execute("DELETE FROM files WHERE task_id = ? AND filename = ?",
                            task_id, secure_filename(file.filename))

            # File stored in directory and database entry storing metadata added
            file.save(os.path.join(
                os.path.join(app.config['UPLOAD_DIRECTORY'], str(task_id)),
                secure_filename(file.filename)
            ))
            db.execute("INSERT INTO files (task_id, filename, uploader, date) values (?, ?, ?, ?)",
                        task_id, secure_filename(file.filename), session["user_id"], datetime.now())

    # Handles excessive file size error
    except RequestEntityTooLarge:
        return "File too large (maximum 16 GB)"

    return redirect(url_for('view', task_id=task_id))


@app.route("/load_file/<filename>/<task_id>")
def load_file(filename, task_id):

    """Delivers quoted file"""

    return send_from_directory(os.path.join(app.config['UPLOAD_DIRECTORY'], str(task_id)), filename)

@app.route("/delete_file/<filename>/<task_id>")
def delete_file(filename, task_id):

    """Deletes given file"""

    # Deletes metadata from database and file from task directory
    db.execute("DELETE FROM files WHERE filename = ? AND task_id = ?", filename, task_id)
    os.remove(os.path.join(os.path.join(app.config['UPLOAD_DIRECTORY'], str(task_id)), filename))

    # Refreshes task view page
    return redirect(url_for('view', task_id=task_id))

@app.route("/opt_out/<task_id>/<user_id>")
@login_required
def opt_out(task_id, user_id):

    """Collaborator quits task"""

    db.execute("DELETE FROM collaborators WHERE task_id = ? AND user_id = ?",
               task_id, user_id)
    return redirect("/")