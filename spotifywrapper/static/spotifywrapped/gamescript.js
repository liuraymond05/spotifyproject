document.addEventListener("DOMContentLoaded", function () {
    let score = 0;
    let currentTrackIndex = 0;
    let timerInterval;
    let timeLeft = 7;
    let gameEnded = false;
    let highScore = localStorage.getItem("highScore") || 0;

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

    // Retrieve track data from the backend
    const tracksElement = document.getElementById("tracks-data");
    let rawData = tracksElement.textContent.trim();


    if (rawData.startsWith("<")) {
        const startIndex = rawData.indexOf("[");
        const endIndex = rawData.lastIndexOf("]");
        rawData = rawData.substring(startIndex, endIndex + 1);
    }
    const tracks = JSON.parse(rawData);
    console.log(rawData.trim());

    // DOM elements for track options
    const optionElements = {
        a: document.getElementById("option-a"),
        b: document.getElementById("option-b"),
        c: document.getElementById("option-c"),
    };

    // Helper function to get random tracks
    function getRandomTracks(trackList, count) {
        const shuffled = trackList.sort(() => 0.5 - Math.random());
        return shuffled.slice(0, count);
    }



    // Load the next track and reset the timer
    function loadTrack() {
        if (currentTrackIndex >= tracks.length) {
            endGame("Game Over! Thanks for playing!");
            return;
        }

        const randomTracks = getRandomTracks(tracks, 3);
        const correctTrack = randomTracks[0];
        console.log(correctTrack);

        // Display album cover
        if (correctTrack.album_cover) {
            albumCoverElement.src = correctTrack.album_cover;
        } else {
            albumCoverElement.src = "path/to/default-image.jpg"; // Use a default image if not available
        }

        // Populate options with song titles
        optionElements.a.textContent = randomTracks[0].title;
        optionElements.b.textContent = randomTracks[1].title;
        optionElements.c.textContent = randomTracks[2].title;

        // Add event listeners to validate user choice
        Object.values(optionElements).forEach((button, index) => {
            button.onclick = () => checkAnswer(randomTracks[index], correctTrack);
        });

        // Reset and start the timer
        timeLeft = 7;
        timerElement.textContent = `Time Left: ${timeLeft}s`;
        clearInterval(timerInterval);
        timerInterval = setInterval(updateTimer, 1000);
    }

    // Function to check the user's answer
    function checkAnswer(selectedTrack, correctTrack) {
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

    // Update the timer
    function updateTimer() {
        timeLeft--;
        timerElement.textContent = `Time Left: ${timeLeft}s`;

        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            endGame("Time's up! Game Over.");
        }
    }

    // Start the game
    startButton.addEventListener("click", () => {
       titleScreen.style.display = "none";
       gamePage.style.display = "block";
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
        gameEnded = false;
        gamePage.style.display = "block";
        endPage.style.display = "none";
        loadTrack();
    });

    returnToStartButton.addEventListener("click", () => {
        titleScreen.style.display = "block";
        gamePage.style.display = "none";
        endPage.style.display = "none";
    });
});