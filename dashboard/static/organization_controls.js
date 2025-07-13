function call_remove_organization(pk) {
    if (!confirm("Are you sure you want to remove this organization? All connected locations will be deleted.")) return;

    fetch(`/remove_organization/${pk}/`)
    .then(response => {
        window.location = "/";
    });
}
