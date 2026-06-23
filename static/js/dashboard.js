document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("cf-sync-form");
    const messageBox = document.getElementById("cf-sync-message");
    const syncBtn = document.getElementById("cf-sync-btn");

    if (!form) return;

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const handle = document.getElementById("cf-handle-input").value.trim();
        if (!handle) {
            messageBox.textContent = "Please enter a Codeforces handle.";
            return;
        }

        syncBtn.disabled = true;
        syncBtn.textContent = "Syncing...";
        messageBox.textContent = "Fetching data from Codeforces...";

        try {
            const formData = new FormData();
            formData.append("handle", handle);

            const response = await fetch("/sync-codeforces", {
                method: "POST",
                body: formData
            });
            const data = await response.json();

            messageBox.textContent = data.message;

            if (data.success) {
                setTimeout(() => window.location.reload(), 1200);
            }
        } catch (err) {
            messageBox.textContent = "Something went wrong while syncing.";
        } finally {
            syncBtn.disabled = false;
            syncBtn.textContent = "Re-sync";
        }
    });
});
