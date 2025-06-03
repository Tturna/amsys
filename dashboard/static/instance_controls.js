function call_stop_instance(app_name) {
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

function call_remove_instance(app_name) {
    fetch(`/remove_instance/${app_name}`)
    .then(response => {
        window.location = "/index";
    });
}
