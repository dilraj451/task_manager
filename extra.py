from functools import wraps
from flask import session, redirect, render_template
from datetime import datetime

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}

def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def persons_and_date(database, data):

    """Add contributor names and deadline to input task data"""

    for row in data:
        row["deadline"] = datetime.strptime(row["deadline"], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%y %H:%M')
        row["creator"] = database.execute("SELECT name FROM users WHERE id IN (SELECT creator_id FROM tasks WHERE id = ?)", row["id"])[0]["name"]
        temp = database.execute("SELECT name FROM users WHERE id IN (SELECT user_id FROM collaborators WHERE task_id = ?)", row["id"])
        cols = []
        for person in temp:
            cols.append(person["name"])
        row["collaborators"] = cols
        if not row["collaborators"]:
            row["collaborators"] = 0
    return data

def get_msgs(database, user_id, task_id):

    """Retrieve and process message data for HTML output"""

    msgs = database.execute("SELECT id, sender_id, content, date FROM messages WHERE task_id = ?", task_id)
    # Processes message meta data
    for msg in msgs:
        msg["date"] = datetime.strptime(msg["date"], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%y %H:%M')
        msg["sender"] = database.execute("SELECT name FROM users WHERE id = ?", msg["sender_id"])[0]["name"]
        if user_id == msg["sender_id"]:
            msg["is_sender"] = True
        else:
            msg["is_sender"] = False
    return msgs

def view_task(database, task_id):

    """Retrieves given task's data from database"""

    task_data = database.execute("SELECT task, deadline, complete FROM tasks WHERE id = ?", task_id)
    task_data[0]["id"] = task_id
    task_data = persons_and_date(database, task_data)
    return task_data[0]

def date_formatter(date):

    """Formats data correctly for entry into database"""

    date = date.replace("-", "/").replace("T", " ")
    date = datetime.strptime(date, '%Y/%m/%d %H:%M')
    return date


def category(database, task_id):

    """Determines task status"""

    cat = database.execute("SELECT deadline, complete FROM tasks WHERE id = ?", task_id)[0]
    cat["deadline"] = datetime.strptime(cat["deadline"], '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%y %H:%M')
    cat["deadline"] = datetime.strptime(cat["deadline"], '%d/%m/%y %H:%M')
    # Three categories possible
    if cat["complete"] == "YES":
        return "completed"
    elif cat["complete"] == "NO" and cat["deadline"] <= current_datetime(datetime.now()):
        return "overdue"
    else:
        return "todo"

def current_datetime(time_date):

    """Formats current date and time for comparison"""

    format = "%d/%m/%y %H:%M"
    time_date = datetime.strftime(time_date, format)
    time_date = datetime.strptime(time_date, format)
    return time_date

def view_date(date):

    """Converts string to datetime datatype"""

    date = datetime.strptime(date, '%d/%m/%y %H:%M')
    return date

def task_table(database, condition, location, user_id):

    """Retrieve task(s) data and outputs for tabulated form"""

    # Extracts key task data from database
    sql_state = "SELECT id, task, deadline FROM tasks WHERE " + condition + " ORDER BY deadline"
    task_data = database.execute(sql_state)
    tasks = []

    if task_data:
        task_data = persons_and_date(database, task_data)
        # Only returns tasks that user involved in
        for task in task_data:
            name = database.execute("SELECT name FROM users WHERE id = ?", user_id)[0]["name"]
            if task["collaborators"] == 0:
                cols = []
            else:
                cols = task["collaborators"]
            if name == task["creator"] or name in cols:
                tasks.append(task)

    if not tasks:
        tasks = 0

    return render_template(location, data=tasks)

def collab_processor(database, persons, task_id, action):

    """"Verifies users submitted/removed as collaborators"""

    # Checks user exists and is not the creator (i.e. administrator)
    collabs = []
    for person in persons:
        if person != "":
            search = database.execute("SELECT id FROM users WHERE lower(name) = ?", person.lower())
            creator = database.execute("SELECT creator_id FROM tasks WHERE id = ?", task_id)[0]["creator_id"]
            if not search:
                return False, person, " does not have an account"
            elif search[0]["id"] == creator:
                return False, person, " is already the administrator"
            else:
                collabs.append(search[0]["id"])

    for collab in collabs:
        # Checks user is not already a collaborator
        if action == "INSERT":
            duplicate = False
            current_collabs = database.execute("SELECT user_id FROM collaborators WHERE task_id = ?", task_id)
            for current in current_collabs:
                if collab == current["user_id"]:
                    duplicate = True
                    break
            if duplicate == False:
                database.execute("INSERT INTO collaborators (task_id, user_id) values (?, ?)", task_id, collab)
        elif action == "DELETE":
            database.execute("DELETE FROM collaborators WHERE task_id = ? AND user_id = ?", task_id, collab)
    return True, True

def access_check(database, user_id, task_id, page):

    """Verfies given user has access to task's page"""

    creator = database.execute("SELECT creator_id FROM tasks WHERE id = ?", task_id)[0]["creator_id"]
    cols = database.execute("SELECT user_id FROM collaborators WHERE task_id = ?", task_id)
    collabs = []
    for col in cols:
        collabs.append(col["user_id"])

    if page == 'VIEW':
        if user_id != creator and user_id not in collabs:
            return False
    elif page == 'EDIT':
        if user_id != creator:
            return False
    else:
        return True

def task_del(database, task_id):

    """Deletes given task's data from database"""

    for table in ["collaborators", "messages", "files", "tasks"]:
        if table == "tasks":
            id = "id"
        else:
            id = "task_id"
        sql_state = f"DELETE FROM {table} WHERE {id} = ?"
        database.execute(sql_state, task_id)