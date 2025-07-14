function call_remove_location(pk) {
    if (!confirm("Are you sure you want to remove this location? All connected apps will be deleted.")) return;

    fetch(`/remove_location/${pk}/`)
    .then(response => {
        window.location = "/";
    });
}
