function call_remove_preset(pk) {
    if (!confirm("Are you sure you want to remove this preset?")) return;

    fetch(`/remove_preset/${pk}/`)
    .then(response => {
        window.location.reload();
    });
}
