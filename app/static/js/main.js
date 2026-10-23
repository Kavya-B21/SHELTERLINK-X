// SHELTERLINK X — Core Client Utilities

document.addEventListener('DOMContentLoaded', function () {
    // Enable Bootstrap tooltips if any
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function () {
        const autoAlerts = document.querySelectorAll('.alert-dismissible');
        autoAlerts.forEach(function (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 6000);
});
