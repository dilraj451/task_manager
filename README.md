# Task Manager
#### Video Demonstration of application: https://youtu.be/yvA1y3UeGX4
#### Before Running Application:
Ensure the following external modules are installed in the local environment: cs50, flask_session. Execute the 'app.py' file to view and use the application.
#### Description:
The project is a utility application utilising Python and SQL backend, as well as Javascript, HTML, and CSS frontend to create a hub for project management and collaboration.

The 'app.py' file contains the routes for the application. The "/" route delivers the homepage ("index.html") that displays any upcoming deadlines the user has in a table.

Each row of the homepage has a button to view ("/view" that links to "view.html") the task details, where the user can update task details ("/edit_details"), upload and view files ("/upload" and "/load_file"), or send messages with fellow participants ("/send_message").

Each row of the homepage also has a button to set the task as completed ("/update") whereby the task is moved to the completed tasks table ("/completed" delivers "completed.html"). Each row of the completed tasks table allows the user to view the task details, although the details can no longer be amended or added to (effictively is archived). Also, buttons to mark the completed task as incomplete ("/update_undo") and to delete the task ("/delete_task") are present on each row. Although, if the task is not completed when the deadline passes, the task is automatically displayed in the overdue tasks table ("/overdue" delivers "overdue.html").

The user can create (and thus be the administrator of) new tasks via the "/create" route that delivers "create.html" where the task name, deadline and collaborators can be submit.

If the user is a collaborator (i.e. not the administrator), there is an 'opt out' button on the view task page which allows the collbarator to quit the task. Also, the back button ("/back") on any view task page returns the user to the previous page.

The 'extra.py' file contains several functions applied in 'app.py' for a variety of purposes, most notably: retrieving task data from the project database ('view_task'); verifying whether a user has access to a given view task page ('access_check'); adding or removing collaborators from a task by checking and executing administrator input ('collab_processor').

The base HTML template extended to each other HTML file is called 'base.html'. The CSS data is stored in 'static/style.css', which primarily sets the style of the chat speech bubbles incorporated in the messaging features.

'project.db' is the database file used to in this project that contains tables named: 'users', 'tasks', 'collaborators', 'messages', 'files'.