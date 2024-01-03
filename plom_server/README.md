# How to run the "new" Plom Server

## Initialise the database

1. Run `python3 manage.py migrate` to setup the database

## Setting up groups and users
Django wants a "super user" to do administrative stuff - they can
access everything. Plom then requires several different groups of
users - admin, manager, marker and scanner. So we need to create those
groups and add the super-user into the admin group.

1. Run `python3 manage.py createsuperuser` to create an admin account (email address is optional)
2. Run `python3 manage.py plom_create_groups` to automatically create admin, manager, marker, and scanner groups. Then, any superusers will be added to the admin group.
3. (Optional) Run `python3 manage.py plom_create_demo_users` to automatically create demo users such as manager, scanners, and markers

Note that if you accidentally do (2) before (1) then you can just run (2) again and it will skip the create-groups bit and just add the superuser to the admin group.


## Running the server

1. To launch the server: `python3 manage.py runserver`

Take note of the address that it tells you the website is running at.

## Log into website with our admin user
1. Open web-browser to "localhost:8000" or whatever the system reported in the "running the server" step above.
2. Log in using your admin account generated above.


## Make a manager instructions (command line)

In order to create a manager, you can log in as asuper user (see below) but its also possible
to use the command line:
```
from django.contrib.auth.models import User, Group
manager_group = Group.objects.get(name='manager')
User.objects.create_user(username='manager', password='1234').groups.add(manager_group)"
```

## Make a manager instructions (web UI)

Go to url: `http://localhost:8000/users`
1. Log in as the admin user
2. Click "create new users"
3. Use the form to create a new Manager account.
4. Copy the generated link and logout of the admin account.
5. Paste the link in the browser's URL bar, or email it to a friend, etc.

Note:
If you forgot the manager username, you can login as the admin user and click on "Password Reset Link".


## Clear existing data from database
This is the command for wiping the existing data from DB:
`python3 manage.py flush`


# For testing (much to do here)

## Run inbuilt tests

1. To run tests: `python3 manage.py test`
