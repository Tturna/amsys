# TODO

Generalize app instance creation to support other kinds of apps.
- Don't force the user to give a container image when creating app instance
- Support running docker compose along with individual container images
- Let the user upload files to instance_template_files or add them manually
  with access to the server.
- Let the user upload/write a custom bash script that will be executed before running
  the app instance. This lets them do whatever is lacking support in the amsys app.
  This is also really dangerous because the user can run intentionally or accidentally
  malicious code.

Make the dynamic form inputs of app creation (like labels, env, volumes...) part of
the form model so the changes persist across a page reload and can be used for
presets in the future.

Go through all used env vars and document them. Make it so no AMSYS vars include
the ADDMAN name.

Application creation presets (ADDMAN, RAPiD-e, option to add custom)

Message framework.

App name validation in instance creation form.
