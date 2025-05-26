function call_stop_instance(app_name) {
    let status_span = document.getElementById(`${app_name}_status`);
    status_span.innerText = "Stopping...";

    let stop_button = document.getElementById(`${app_name}_stop_button`);
    stop_button.disabled = true;

    fetch(`/stop_instance/${app_name}`)
    .then(response => {
        console.log(response);
        status_span.innerText = "Stopped";
        window.location.reload();
    });
}
