const words = JSON.parse(localStorage.getItem("kannadaWords")) || [];

const question = document.getElementById("question");
const options = document.getElementById("options");
const feedback = document.getElementById("feedback");
const nextButton = document.getElementById("nextButton");

let currentWord = null;
let score = 0;
let answered = false;

function loadQuestion() {
    options.innerHTML = "";
    feedback.textContent = "";
    nextButton.style.display = "none";
    answered = false;

    if (words.length < 2) {
        question.textContent =
            "Add at least 2 words to your Kannada Bank to start practicing.";

        return;
    }

    currentWord = words[Math.floor(Math.random() * words.length)];

    question.innerHTML = `
        What does <strong>${currentWord.word}</strong> mean?
        <br><br>
        Score: ${score}
    `;

    // Correct answer
    const answers = [currentWord.english];

    // Add other saved words as wrong answers
    const otherWords = words.filter(
        word => word.word !== currentWord.word
    );

    otherWords.forEach(word => {
        if (answers.length < 4) {
            answers.push(word.english);
        }
    });

    // Shuffle answer options
    answers.sort(() => Math.random() - 0.5);

    answers.forEach(answer => {
        const button = document.createElement("button");
        button.textContent = answer;
        button.style.display = "block";
        button.style.margin = "10px 0";

        button.onclick = function () {
            checkAnswer(answer);
        };

        options.appendChild(button);
    });
}

function checkAnswer(answer) {
    if (answered) return;

    answered = true;

    const optionButtons = options.querySelectorAll("button");

    optionButtons.forEach(button => {
        button.disabled = true;

        if (button.textContent === currentWord.english) {
            button.style.fontWeight = "bold";
        }
    });

    if (answer === currentWord.english) {
        score++;
        feedback.textContent = "Correct! Well done.";
    } else {
        feedback.textContent =
            "Not quite. The correct answer is: " +
            currentWord.english;
    }

    nextButton.style.display = "block";
}

nextButton.addEventListener("click", loadQuestion);

loadQuestion();