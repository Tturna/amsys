function call_start_proxy() {
    let status_span = document.getElementById("proxy_status");

    if (status_span) {
        status_span.innerText = "Proxy starting...";
    }

    let start_button = document.getElementById("proxy_start_button");

    if (start_button) {
        start_button.disabled = true;
    }

    fetch("/start_proxy/")
    .then(response => {
        window.location.reload();
    });
}

function call_stop_proxy() {
    if (!confirm("Are you sure you want to stop the proxy? This will prevent access to any app instances until it is restarted.")) {
        return;
    }

    let status_span = document.getElementById("proxy_status");

    if (status_span) {
        status_span.innerText = "Proxy stopping...";
    }

    let stop_button = document.getElementById("proxy_stop_button");

    if (stop_button) {
        stop_button.disabled = true;
    }

    fetch("/stop_proxy/")
    .then(response => {
        window.location.reload();
    });

}
