# TODO

Generalize app instance creation to support other kinds of apps.
- Let the user upload files to instance_template_files or add them manually
  with access to the server.
- Let the user upload/write a custom bash script that will be executed before running
  the app instance. This lets them do whatever is lacking support in the amsys app.
  This is also really dangerous because the user can run intentionally or accidentally
  malicious code.

API token max length needs to be higher. Instance changes in the admin panel may not work.

Free text field to instances where you can specify the server on which the app is running for example.

File transfer logging somehow?

Show the owner organization of locations when creating an instance

API connection lines should be different based on connected app/location status.

Separate out app listing so it can be easily used in many places.
- Show app location and connected organization in the listed cards.
- Fix "created at" (timezone).

Make it so the index page, view instance page etc. don't hard code the instance domain
to localhost.

Remove hard coded fetch and window location paths from JS.

Add instructions and validation for compose files.

Consider refactoring views.py and splitting it into multiple files.

Add automated testing.

Make it so files created by compose based apps can be deleted by the master app.
For image based apps, this is done by setting the container's UID to match the UID
that runs the master app. For compose, you can't do this from the command line.

When an instance asks for an SSH certificate (e.g. for SFTP file transfer),
sign the cert so it can only be used to access the requested target, if allowed.
Currently the certificate can be used to access any instance. This is only really
an issue if someone creates a malicious app that is then executed by AMSYS.
