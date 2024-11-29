document.addEventListener("DOMContentLoaded", function () {
    let score = 0;
    let currentTrackIndex = 0;
    let timerInterval;
    let totalGameTime = 30; // Set total game time in seconds
    let gameEnded = false;
    let highScore = localStorage.getItem("highScore") || 0;
    let hintsRemaining = 3; // User gets three hints per game
    let correctTrack; // Track the correct answer for hints

    // DOM Elements
    const titleScreen = document.getElementById("title-screen");
    const gamePage = document.getElementById("game-page");
    const endPage = document.getElementById("end-page");
    const albumCoverElement = document.getElementById("album-cover");
    const scoreElement = document.getElementById("score");
    const timerElement = document.getElementById("timer");
    const finalScoreElement = document.getElementById("final-score");
    const highScoreElement = document.getElementById("high-score");
    const playAgainButton = document.getElementById("play-again");
    const returnToStartButton = document.getElementById("return-to-start");
    const startButton = document.getElementById("start-button");
    const howToPlayButton = document.getElementById("how-to-play-button");
    const instructionsModal = document.getElementById("instructions-modal");
    const closeInstructionsButton = document.getElementById("close-instructions");
    const hintButton = document.getElementById("hint-button");
    //reset high score button stuff
    const resetHighScoreButton = document.createElement("button");
    resetHighScoreButton.id = "reset-high-score";
    resetHighScoreButton.textContent = "Reset High Score";
    resetHighScoreButton.classList.add("hint-button"); // Assuming 'hint-button-style' styles your hint button
    endPage.appendChild(resetHighScoreButton); // Append to end page


    // DOM elements for track options
    const optionElements = {
        a: document.getElementById("option-a"),
        b: document.getElementById("option-b"),
        c: document.getElementById("option-c"),
    };

    // Open "How to Play" Modal
    howToPlayButton.addEventListener("click", () => {
        instructionsModal.style.display = "flex";
    });

    // Close "How to Play" Modal
    closeInstructionsButton.addEventListener("click", () => {
        instructionsModal.style.display = "none";
    });

    instructionsModal.addEventListener("click", (e) => {
        if (e.target === instructionsModal) {
            instructionsModal.style.display = "none";
        }
    });

    // Retrieve track data from the backend
    const tracksElement = document.getElementById("tracks-data");
    let rawData = tracksElement.textContent.trim();

    if (rawData.startsWith("<")) {
        const startIndex = rawData.indexOf("[");
        const endIndex = rawData.lastIndexOf("]");
        rawData = rawData.substring(startIndex, endIndex + 1);
    }
    const tracks = JSON.parse(rawData);

    // Helper function to get random tracks
    function getRandomTracks(trackList, count) {
        const shuffled = trackList.sort(() => 0.5 - Math.random());
        return shuffled.slice(0, count);
    }

    // Load the next track
    function loadTrack() {
        if (currentTrackIndex >= tracks.length) {
            endGame("Game Over! Thanks for playing!");
            return;
        }

        const randomTracks = getRandomTracks(tracks, 3);
        correctTrack = randomTracks[0];
        const shuffledTracks = randomTracks.sort(() => Math.random() - 0.5);

        albumCoverElement.src = correctTrack.album_cover || "path/to/default-image.jpg";

        Object.values(optionElements).forEach((button, index) => {
            button.textContent = shuffledTracks[index].title;
            button.onclick = () => checkAnswer(shuffledTracks[index]);
            button.style.pointerEvents = "auto"; // Reset for reusability
            button.classList.remove("disabled"); // Reset hint styles
        });

        hintButton.disabled = hintsRemaining === 0; // Disable hint button if no hints left
        hintButton.textContent = `Hint (${hintsRemaining} left)`;
    }

    // Check the user's answer
    function checkAnswer(selectedTrack) {
        if (gameEnded) return;

        if (selectedTrack.id === correctTrack.id) {
            alert("Correct!");
            score += 3;
        } else {
            alert("Incorrect!");
            score -= 1;
        }

        scoreElement.textContent = `Score: ${score}`;
        currentTrackIndex++;
        loadTrack();
    }

    // Use a hint
    function useHint() {
        if (hintsRemaining <= 0 || gameEnded) return;

        hintsRemaining--;
        hintButton.textContent = `Hint (${hintsRemaining} left)`;

        // Find all incorrect options
        const incorrectOptions = Object.values(optionElements).filter(
            (button) => button.textContent !== correctTrack.title && !button.classList.contains("disabled")
        );

        if (incorrectOptions.length > 0) {
            const optionToDisable = incorrectOptions[0]; // Disable the first incorrect option
            optionToDisable.classList.add("disabled");
            optionToDisable.style.pointerEvents = "none"; // Make it unclickable
        }

        if (hintsRemaining === 0) {
            hintButton.disabled = true; // Disable hint button if no hints remain
        }
    }

    // Update the game timer
    function updateTimer() {
        totalGameTime--;
        timerElement.textContent = `Time Left: ${totalGameTime}s`;

        if (totalGameTime <= 0) {
            clearInterval(timerInterval);
            endGame("Time's up! Game Over.");
        }
    }

    // Start the game
    startButton.addEventListener("click", () => {
        titleScreen.style.display = "none";
        gamePage.style.display = "block";
        timerElement.textContent = `Time Left: ${totalGameTime}s`;

        timerInterval = setInterval(updateTimer, 1000);
        loadTrack();
    });

    // End the game
    function endGame(message) {
        gameEnded = true;
        clearInterval(timerInterval);
        gamePage.style.display = "none";
        endPage.style.display = "block";
        finalScoreElement.textContent = `Your Score: ${score}`;
        if (score > highScore) {
            highScore = score;
            localStorage.setItem("highScore", highScore);
        }
        highScoreElement.textContent = `High Score: ${highScore}`;
    }

    // Reset the game
    playAgainButton.addEventListener("click", () => {
        score = 0;
        currentTrackIndex = 0;
        totalGameTime = 30;
        hintsRemaining = 3; // Reset hints
        gameEnded = false;
        gamePage.style.display = "block";
        endPage.style.display = "none";
        timerElement.textContent = `Time Left: ${totalGameTime}s`;
        timerInterval = setInterval(updateTimer, 1000);
        loadTrack();
    });

    returnToStartButton.addEventListener("click", () => {
        titleScreen.style.display = "block";
        gamePage.style.display = "none";
        endPage.style.display = "none";
        clearInterval(timerInterval);
    });

    // Add event listener for hint button
    hintButton.addEventListener("click", useHint);

    // Reset High Score functionality
    resetHighScoreButton.addEventListener("click", () => {
        const userConfirmed = confirm("Are you sure? This action cannot be undone.");
        if (userConfirmed) {
            highScore = 0;
            localStorage.setItem("highScore", highScore);
            highScoreElement.textContent = `High Score: ${highScore}`;
            alert("High score has been reset!");
        }
    });
});
