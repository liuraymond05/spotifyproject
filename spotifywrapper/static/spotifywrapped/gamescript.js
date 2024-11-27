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
    const lyricElement = document.getElementById("lyric");
    const scoreElement = document.getElementById("score");
    const timerElement = document.getElementById("timer");
    const finalScoreElement = document.getElementById("final-score");
    const highScoreElement = document.getElementById("high-score");
    const playAgainButton = document.getElementById("play-again");
    const returnToStartButton = document.getElementById("return-to-start");



    const startButton = document.getElementById("start-button");
//    if (startButton) {
//        console.log("Setting start button");
//        startButton.addEventListener("click", startGame); // This will start the game when the button is clicked
//    }

    document.getElementById("start-button").addEventListener("click", startGame);

    // Retrieve the tracks data from the script tag and parse it
    const tracksElement = document.getElementById('tracks-data');
    rawData = tracksElement.textContent.trim();
    // Strip out anything that isn't JSON (if necessary)
    if (rawData.startsWith("<")) {
        const startIndex = rawData.indexOf("[");
        const endIndex = rawData.lastIndexOf("]");
        rawData = rawData.substring(startIndex, endIndex + 1);
    }
    console.log(rawData.trim());
    const tracks = JSON.parse(rawData.trim());

    // Now you can use the tracks object in your game logic
    //console.log(tracks);  // Check the data


    // Helper function to get random tracks
    function getRandomTracks(trackList, count) {
        const shuffled = trackList.sort(() => 0.5 - Math.random());
        return shuffled.slice(0, count);
    }

//    let score = 0;
//    let currentTrackIndex = 0;
//    let timerInterval;
//    let timeLeft = 7;
//    let gameEnded = false;
//    let highScore = localStorage.getItem("highScore") || 0;
//
//    // DOM Elements
//    const titleScreen = document.getElementById("title-screen");
//    const gamePage = document.getElementById("game-page");
//    const endPage = document.getElementById("end-page");
//    const lyricElement = document.getElementById("lyric");
//    const scoreElement = document.getElementById("score");
//    const timerElement = document.getElementById("timer");
//    const finalScoreElement = document.getElementById("final-score");
//    const highScoreElement = document.getElementById("high-score");
//    const playAgainButton = document.getElementById("play-again");
//    const returnToStartButton = document.getElementById("return-to-start");

    const optionElements = {
        a: document.getElementById("option-a"),
        b: document.getElementById("option-b"),
        c: document.getElementById("option-c")
    };

    // Function to load the next track and reset the timer
    function loadTrack() {
        const randomTracks = getRandomTracks(tracks, 3); // Get 3 random tracks for the round

        // Select one track for the lyric (for simplicity, using the first track in the list)
        const selectedTrack = randomTracks[0];

        // Update lyric placeholder (you will need to add logic to fetch lyrics from Genius API)
        lyricElement.textContent = "Fetching lyric...";  // Placeholder text

        optionElements.a.querySelector("p").textContent = `A. ${randomTracks[0].title}`;
        optionElements.b.querySelector("p").textContent = `B. ${randomTracks[1].title}`;
        optionElements.c.querySelector("p").textContent = `C. ${randomTracks[2].title}`;

        // Set album covers for the options using the image URL from Spotify API
        optionElements.a.querySelector("img").src = randomTracks[0].album.images[0].url;
        optionElements.b.querySelector("img").src = randomTracks[1].album.images[0].url;
        optionElements.c.querySelector("img").src = randomTracks[2].album.images[0].url;

        timeLeft = 7;
        timerElement.textContent = `Time Left: ${timeLeft}s`;
        clearInterval(timerInterval);
        timerInterval = setInterval(updateTimer, 1000);
    }


    // Function to start the game
    function startGame() {
        console.log("Trying to start game");
        titleScreen.style.display = "none";
        gamePage.style.display = "block";
        loadTrack();
    }


    // Function to update the timer
    function updateTimer() {
        timeLeft--;
        timerElement.textContent = `Time Left: ${timeLeft}s`;

        if (timeLeft <= 0) {
            clearInterval(timerInterval);
            endGame("Time's up! Game Over.");
        }
    }

    // Function to handle option clicks
    function handleOptionClick(selectedOption) {
        if (gameEnded) return;

        const correctTrack = tracks[currentTrackIndex];

        // Logic to check if the selected track is correct
        if (selectedOption === correctTrack.id) {
            score += 3;
            nextRound();
        } else {
            score -= 1;
            alert("Incorrect!");
        }

        scoreElement.textContent = `Score: ${score}`;
    }

    // Add event listeners to options
    Object.keys(optionElements).forEach((key) => {
        optionElements[key].addEventListener("click", () => handleOptionClick(key));
    });

    // Function to proceed to the next round or end the game if no more rounds
    function nextRound() {
        currentTrackIndex++;
        if (currentTrackIndex >= tracks.length) {
            endGame("Game Over! Thanks for playing!");
        } else {
            loadTrack();
        }
    }

    // Function to end the game
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

    // Play Again Button
    playAgainButton.addEventListener("click", () => {
        resetGame();
        endPage.style.display = "none";
        gamePage.style.display = "block";
    });

    // Return to Start Button
    returnToStartButton.addEventListener("click", () => {
        resetGame();
        endPage.style.display = "none";
        titleScreen.style.display = "block";
    });

    // Reset Game
    function resetGame() {
        score = 0;
        currentTrackIndex = 0;
        gameEnded = false;
        scoreElement.textContent = `Score: 0`;
        loadTrack();
    }
});
