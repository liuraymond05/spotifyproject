// Placeholder data to simulate Spotify top tracks and lyrics
const lyrics = [
  {
    lyric: "Cause the players gonna play, play, play, play, play",
    correct: "a",
    options: ["Shake It Off", "Someone Like You", "Blinding Lights"]
  },
  {
    lyric: "We don’t talk about Bruno, no, no, no",
    correct: "b",
    options: ["Perfect", "We Don’t Talk About Bruno", "Rolling in the Deep"]
  },
  {
    lyric: "I’m gonna take my horse to the old town road",
    correct: "c",
    options: ["Bad Guy", "Happier", "Old Town Road"]
  }
];

let score = 0;
let currentLyricIndex = 0;
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

const optionElements = {
  a: document.getElementById("option-a"),
  b: document.getElementById("option-b"),
  c: document.getElementById("option-c")
};

// Function to start the game
function startGame() {
  titleScreen.style.display = "none";
  gamePage.style.display = "block";
  loadLyric();
  titleScreen.removeEventListener("click", startGame); // Remove click listener after starting
}



// Function to load the next lyric and reset the timer
function loadLyric() {
  const { lyric, options } = lyrics[currentLyricIndex];
  lyricElement.textContent = lyric;
  optionElements.a.querySelector("p").textContent = `A. ${options[0]}`;
  optionElements.b.querySelector("p").textContent = `B. ${options[1]}`;
  optionElements.c.querySelector("p").textContent = `C. ${options[2]}`;

  timeLeft = 7;
  timerElement.textContent = `Time Left: ${timeLeft}s`;
  clearInterval(timerInterval);
  timerInterval = setInterval(updateTimer, 1000);
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

  const correctAnswer = lyrics[currentLyricIndex].correct;

  if (selectedOption === correctAnswer) {
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
  currentLyricIndex++;
  if (currentLyricIndex >= lyrics.length) {
    endGame("Game Over! Thanks for playing!");
  } else {
    loadLyric();
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
  currentLyricIndex = 0;
  gameEnded = false;
  scoreElement.textContent = `Score: 0`;
  loadLyric();
}

// Event listener for the "Click to Begin" button
document.getElementById("start-button").addEventListener("click", function () {
  document.getElementById("title-screen").style.display = "none";
  document.getElementById("game-page").style.display = "block";
  loadLyric(); // Start the game by loading the first lyric
});