const CF_TOPICS = [
    "dp", "greedy", "math", "graphs", "implementation", "data structures",
    "strings", "brute force", "binary search", "dfs and similar",
    "trees", "number theory", "combinatorics", "sortings",
    "two pointers", "constructive algorithms", "geometry", "bitmasks"
];

const RATING_VALUES = [];
for (let r = 800; r <= 3500; r += 100) RATING_VALUES.push(r);

const selectedTopics = new Set();

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
    CF_TOPICS.forEach(topic => {
        const chip = document.createElement("span");
        chip.textContent = topic + "  ";
        chip.style.cursor = "pointer";
        chip.addEventListener("click", () => {
            if (selectedTopics.has(topic)) {
                selectedTopics.delete(topic);
                chip.style.fontWeight = "normal";
            } else {
                selectedTopics.add(topic);
                chip.style.fontWeight = "bold";
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
        messageBox.textContent = "Min rating cannot be greater than max rating.";
        return;
    }

    btn.disabled = true;
    btn.textContent = "Generating...";
    messageBox.textContent = "Checking problems against your solved history...";

    try {
        const response = await fetch("/api/generate-contest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                title: title,
                rating_min: ratingMin,
                rating_max: ratingMax,
                topics: Array.from(selectedTopics),
                num_questions: numQuestions
            })
        });
        const data = await response.json();

        if (data.success) {
            messageBox.textContent = "Contest generated! Redirecting...";
            setTimeout(() => {
                window.location.href = "/contest/" + data.contest_id;
            }, 800);
        } else {
            messageBox.textContent = data.message;
        }
    } catch (err) {
        messageBox.textContent = "Something went wrong. Please try again.";
    } finally {
        btn.disabled = false;
        btn.textContent = "Generate Contest";
    }
}
