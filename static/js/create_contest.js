const CF_TOPICS = [
    "dp", "greedy", "math", "graphs", "implementation", "data structures",
    "strings", "brute force", "binary search", "dfs and similar",
    "trees", "number theory", "combinatorics", "sortings",
    "two pointers", "constructive algorithms", "geometry", "bitmasks"
];

const ALL_TOPICS_LABEL = "All Topics";

const RATING_VALUES = [];
for (let r = 800; r <= 3500; r += 100) RATING_VALUES.push(r);

const selectedTopics = new Set();
let allTopicsSelected = true;

document.addEventListener("DOMContentLoaded", function () {
    populateRatingSelects();
    populateTopicChips();

    const generateBtn = document.getElementById("generate-btn");
    if (generateBtn) {
        generateBtn.addEventListener("click", handleGenerate);
    }
});

function populateRatingSelects() {
    const minSelect = document.getElementById("rating_min");
    const maxSelect = document.getElementById("rating_max");

    RATING_VALUES.forEach(r => {
        const optMin = document.createElement("option");
        optMin.value = r;
        optMin.textContent = r;
        minSelect.appendChild(optMin);

        const optMax = document.createElement("option");
        optMax.value = r;
        optMax.textContent = r;
        maxSelect.appendChild(optMax);
    });

    minSelect.value = 800;
    maxSelect.value = 1200;
}

function populateTopicChips() {
    const grid = document.getElementById("topics-grid");
    grid.innerHTML = "";

    const allChip = document.createElement("div");
    allChip.className = "topic-chip topic-chip-all selected";
    allChip.textContent = ALL_TOPICS_LABEL;
    allChip.addEventListener("click", () => {
        allTopicsSelected = true;
        selectedTopics.clear();
        Array.from(grid.children).forEach(chip => {
            chip.classList.toggle("selected", chip === allChip);
        });
    });
    grid.appendChild(allChip);

    CF_TOPICS.forEach(topic => {
        const chip = document.createElement("div");
        chip.className = "topic-chip";
        chip.textContent = topic;
        chip.addEventListener("click", () => {
            if (selectedTopics.has(topic)) {
                selectedTopics.delete(topic);
                chip.classList.remove("selected");
            } else {
                selectedTopics.add(topic);
                chip.classList.add("selected");
            }

            if (selectedTopics.size > 0) {
                allTopicsSelected = false;
                allChip.classList.remove("selected");
            } else {
                allTopicsSelected = true;
                allChip.classList.add("selected");
            }
        });
        grid.appendChild(chip);
    });
}

async function handleGenerate() {
    const title = document.getElementById("title").value.trim();
    const ratingMin = parseInt(document.getElementById("rating_min").value);
    const ratingMax = parseInt(document.getElementById("rating_max").value);
    const numQuestions = parseInt(document.getElementById("num_questions").value);
    const messageBox = document.getElementById("generate-message");
    const btn = document.getElementById("generate-btn");

    if (ratingMin > ratingMax) {
        showMessage(messageBox, "Min rating cannot be greater than max rating.", "error");
        return;
    }

    btn.disabled = true;
    btn.textContent = "Generating...";
    showMessage(messageBox, "Checking Codeforces problems against your solved history...", "");

    try {
        const response = await fetch("/api/generate-contest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: title,
                rating_min: ratingMin,
                rating_max: ratingMax,
                topics: allTopicsSelected ? [] : Array.from(selectedTopics),
                num_questions: numQuestions
            })
        });
        const data = await response.json();

        if (data.success) {
            showMessage(messageBox, "Contest generated! Redirecting...", "success");
            setTimeout(() => {
                window.location.href = "/contest/" + data.contest_id;
            }, 800);
        } else {
            showMessage(messageBox, data.message, "error");
        }
    } catch (err) {
        showMessage(messageBox, "Something went wrong. Please try again.", "error");
    } finally {
        btn.disabled = false;
        btn.textContent = "Generate Contest";
    }
}

function showMessage(box, text, type) {
    box.textContent = text;
    box.className = "cf-sync-message" + (type ? " " + type : "");
}
