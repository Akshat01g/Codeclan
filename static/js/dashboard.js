document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("cf-sync-form");
    const messageBox = document.getElementById("cf-sync-message");
    const syncBtn = document.getElementById("cf-sync-btn");

    if (!form) return;

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const handle = document.getElementById("cf-handle-input").value.trim();
        if (!handle) {
            showMessage("Please enter a Codeforces handle.", "error");
            return;
        }

        syncBtn.disabled = true;
        syncBtn.textContent = "Syncing";
        showMessage("Fetching data from Codeforces, this may take a few seconds", "");

        try {
            const formData = new FormData();
            formData.append("handle", handle);

            const response = await fetch("/sync-codeforces", {
                method: "POST",
                body: formData
            });
            const data = await response.json();

            if (data.success) {
                showMessage(data.message, "success");
                setTimeout(() => window.location.reload(), 1200);
            } else {
                showMessage(data.message, "error");
            }
        } catch (err) {
            showMessage("Something went wrong while syncing.Try again.", "error");
        } finally {
            syncBtn.disabled = false;
            syncBtn.textContent = "Re-sync";
        }
    });

    function showMessage(text, type) {
        messageBox.textContent = text;
        messageBox.className = "cf-sync-message" + (type ? " " + type : "");
    }
});
