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
let currentMode = "range";

let individualQuestionState = [];

document.addEventListener("DOMContentLoaded", function () {
    populateRatingSelects();
    populateTopicChipsInto(document.getElementById("topics-grid"), selectedTopics,
        () => allTopicsSelected, (v) => { allTopicsSelected = v; });

    document.getElementById("mode-range-btn").addEventListener("click", () => switchMode("range"));
    document.getElementById("mode-individual-btn").addEventListener("click", () => switchMode("individual"));

    document.getElementById("num_questions").addEventListener("change", () => {
        if (currentMode === "individual") buildIndividualQuestionForm();
    });

    const generateBtn = document.getElementById("generate-btn");
    if (generateBtn) {
        generateBtn.addEventListener("click", handleGenerate);
    }
});

function switchMode(mode) {
    currentMode = mode;

    document.getElementById("mode-range-btn").classList.toggle("selected", mode === "range");
    document.getElementById("mode-individual-btn").classList.toggle("selected", mode === "individual");

    document.getElementById("range-mode-section").classList.toggle("hidden", mode !== "range");
    document.getElementById("individual-mode-section").classList.toggle("hidden", mode !== "individual");

    if (mode === "individual") {
        buildIndividualQuestionForm();
    }
}

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

function populateTopicChipsInto(grid, selectedSet, getAllFlag, setAllFlag) {
    grid.innerHTML = "";

    const allChip = document.createElement("div");
    allChip.className = "topic-chip topic-chip-all" + (getAllFlag() ? " selected" : "");
    allChip.textContent = ALL_TOPICS_LABEL;
    allChip.addEventListener("click", () => {
        setAllFlag(true);
        selectedSet.clear();
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
            if (selectedSet.has(topic)) {
                selectedSet.delete(topic);
                chip.classList.remove("selected");
            } else {
                selectedSet.add(topic);
                chip.classList.add("selected");
            }

            if (selectedSet.size > 0) {
                setAllFlag(false);
                allChip.classList.remove("selected");
            } else {
                setAllFlag(true);
                allChip.classList.add("selected");
            }
        });
        grid.appendChild(chip);
    });
}

function buildIndividualQuestionForm() {
    const numQuestions = parseInt(document.getElementById("num_questions").value);
    const container = document.getElementById("individual-questions-container");
    container.innerHTML = "";

    const newState = [];
    for (let i = 0; i < numQuestions; i++) {
        if (individualQuestionState[i]) {
            newState.push(individualQuestionState[i]);
        } else {
            newState.push({ rating: 1200, allTopics: true, topics: new Set() });
        }
    }
    individualQuestionState = newState;

    individualQuestionState.forEach((state, idx) => {
        const block = document.createElement("div");
        block.className = "individual-question-block";

        const heading = document.createElement("h4");
        heading.textContent = `Question ${idx + 1}`;
        block.appendChild(heading);

        const ratingGroup = document.createElement("div");
        ratingGroup.className = "form-group";
        const ratingLabel = document.createElement("label");
        ratingLabel.textContent = "Rating";
        const ratingSelect = document.createElement("select");
        RATING_VALUES.forEach(r => {
            const opt = document.createElement("option");
            opt.value = r;
            opt.textContent = r;
            if (r === state.rating) opt.selected = true;
            ratingSelect.appendChild(opt);
        });
        ratingSelect.addEventListener("change", () => {
            state.rating = parseInt(ratingSelect.value);
        });
        ratingGroup.appendChild(ratingLabel);
        ratingGroup.appendChild(ratingSelect);
        block.appendChild(ratingGroup);

        const topicsGroup = document.createElement("div");
        topicsGroup.className = "form-group";
        const topicsLabel = document.createElement("label");
        topicsLabel.textContent = "Topics";
        const topicsGrid = document.createElement("div");
        topicsGrid.className = "topics-grid";
        topicsGroup.appendChild(topicsLabel);
        topicsGroup.appendChild(topicsGrid);
        block.appendChild(topicsGroup);

        populateTopicChipsInto(
            topicsGrid,
            state.topics,
            () => state.allTopics,
            (v) => { state.allTopics = v; }
        );

        container.appendChild(block);
    });
}

async function handleGenerate() {
    const title = document.getElementById("title").value.trim();
    const numQuestions = parseInt(document.getElementById("num_questions").value);
    const messageBox = document.getElementById("generate-message");
    const btn = document.getElementById("generate-btn");

    let payload = {
        title: title,
        num_questions: numQuestions,
        mode: currentMode
    };

    if (currentMode === "range") {
        const ratingMin = parseInt(document.getElementById("rating_min").value);
        const ratingMax = parseInt(document.getElementById("rating_max").value);

        if (ratingMin > ratingMax) {
            showMessage(messageBox, "Min rating cannot be greater than max rating.", "error");
            return;
        }

        payload.rating_min = ratingMin;
        payload.rating_max = ratingMax;
        payload.topics = allTopicsSelected ? [] : Array.from(selectedTopics);
    } else {
        payload.questions = individualQuestionState.map(state => ({
            rating: state.rating,
            topics: state.allTopics ? [] : Array.from(state.topics)
        }));
    }

    btn.disabled = true;
    btn.textContent = "Generating...";
    showMessage(messageBox, "Checking Codeforces problems against your solved history...", "");

    try {
        const response = await fetch("/api/generate-contest", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
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
