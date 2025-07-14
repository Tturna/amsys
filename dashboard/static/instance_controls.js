function call_stop_instance(app_name) {
    if (!confirm(`Are you sure you want to stop instance "${app_name}"?`)) {
        return;
    }

    let status_span = document.getElementById(`${app_name}_status`);

    if (status_span) {
        status_span.innerText = "Stopping...";
    }

    let stop_button = document.getElementById(`${app_name}_stop_button`);

    if (stop_button) {
        stop_button.disabled = true;
    }

    fetch(`/stop_instance/${app_name}`)
    .then(response => {
        if (status_span) {
            status_span.innerText = "Stopped";
        }

        window.location.reload();
    });
}

function call_kill_instance(app_name) {
    if (!confirm(`Are you sure you want to forcibly kill instance "${app_name}"?`)) {
        return;
    }

    let status_span = document.getElementById(`${app_name}_status`);

    if (status_span) {
        status_span.innerText = "Killing...";
    }

    let kill_button = document.getElementById(`${app_name}_kill_button`);

    if (kill_button) {
        kill_button.disabled = true;
    }

    fetch(`/stop_instance/${app_name}/True`)
    .then(response => {
        if (status_span) {
            status_span.innerText = "Stopped";
        }

        window.location.reload();
    });
}

function call_start_instance(app_name) {
    let status_span = document.getElementById(`${app_name}_status`);

    if (status_span) {
        status_span.innerText = "Starting...";
    }

    let start_button = document.getElementById(`${app_name}_start_button`);

    if (start_button) {
        start_button.disabled = true;
    }

    fetch(`/start_instance/${app_name}`)
    .then(response => {
        window.location = "/";
    });
}

function call_restart_instance(app_name) {
    let status_span = document.getElementById(`${app_name}_status`);

    if (status_span) {
        status_span.innerText = "Restarting...";
    }

    let restart_button = document.getElementById(`${app_name}_restart_button`);

    if (restart_button) {
        restart_button.disabled = true;
    }

    fetch(`/restart_instance/${app_name}`)
    .then(response => {
        window.location = "/";
    });
}

function call_remove_instance(app_name) {
    if (!confirm(`Are you sure you want to permanently remove instance "${app_name}"? All data will be lost. This can not be undone.`)) {
        return;
    }

    fetch(`/remove_instance/${app_name}`)
    .then(response => {
        window.location = "/";
    });
}

function call_forget_instance(app_name) {
    if (!confirm(`Are you sure you want to permanently forget instance "${app_name}"? The instance can not be started anymore.`)) {
        return;
    }

    fetch(`/forget_instance/${app_name}`)
    .then(response => {
        window.location = "/";
    });
}
