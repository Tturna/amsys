# TODO

Generalize app instance creation to support other kinds of apps.
- Let the user upload files to instance_template_files or add them manually
  with access to the server.
- Let the user upload/write a custom bash script that will be executed before running
  the app instance. This lets them do whatever is lacking support in the amsys app.
  This is also really dangerous because the user can run intentionally or accidentally
  malicious code.

Add instructions and validation for compose files.

Let the user set the user with which to run containers.

Fix bug where an app named "test" will match with existing containers named like "addman-test".

Lines between orgs in the map depending on connected instances.
- Lines should be different if the orgs have a lot of connected app instances

Go through all used env vars and document them. Make it so no AMSYS vars include
the ADDMAN name.

Make it so the index page, view instance page etc. don't hard code the instance domain
to localhost.

App name validation in instance creation form.

Make it so files created by compose based apps can be deleted by the master app.
For image based apps, this is done by setting the container's UID to match the UID
that runs the master app. For compose, you can't do this from the command line.

When an instance asks for an SSH certificate (e.g. for SFTP file transfer),
sign the cert so it can only be used to access the requested target, if allowed.
Currently the certificate can be used to access any instance. This is only really
an issue if someone creates a malicious app that is then executed by AMSYS.
