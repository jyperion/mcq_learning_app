// State management
let currentQuestion = null;
let score = 0;
let questionsAnswered = 0;

// DOM Elements
const questionText = document.getElementById('questionText');
const optionsSection = document.getElementById('optionsSection');
const feedbackSection = document.getElementById('feedbackSection');
const recheckSection = document.getElementById('recheckSection');
const submitButton = document.getElementById('submitAnswer');
const nextButton = document.getElementById('nextQuestion');
const scoreElement = document.getElementById('score');
const questionsAnsweredElement = document.getElementById('questionsAnswered');
const progressSection = document.getElementById('progressSection');

// Initialize the page
async function initializePractice() {
    await loadNextQuestion();
    progressSection.classList.remove('hidden');
}

// Load a new question
async function loadNextQuestion() {
    try {
        const response = await fetch('/api/questions/random');
        if (!response.ok) throw new Error('Failed to fetch question');
        
        currentQuestion = await response.json();
        displayQuestion(currentQuestion);
        
        // Reset UI state
        submitButton.classList.remove('hidden');
        nextButton.classList.add('hidden');
        feedbackSection.classList.add('hidden');
        recheckSection.classList.add('hidden');
    } catch (error) {
        showError('Failed to load question: ' + error.message);
    }
}

// Display the current question
function displayQuestion(question) {
    questionText.textContent = question.text;
    optionsSection.innerHTML = '';
    
    question.options.forEach((option, index) => {
        const optionDiv = document.createElement('div');
        optionDiv.className = 'flex items-center space-x-3';
        
        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = 'answer';
        radio.value = index;
        radio.id = `option${index}`;
        radio.className = 'form-radio h-4 w-4 text-indigo-600';
        
        const label = document.createElement('label');
        label.htmlFor = `option${index}`;
        label.textContent = option;
        label.className = 'text-gray-700';
        
        optionDiv.appendChild(radio);
        optionDiv.appendChild(label);
        optionsSection.appendChild(optionDiv);
    });
}

// Handle answer submission
async function submitAnswer() {
    const selectedOption = document.querySelector('input[name="answer"]:checked');
    if (!selectedOption) {
        showError('Please select an answer');
        return;
    }
    
    try {
        const response = await fetch(`/api/questions/${currentQuestion.id}/check`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answer: parseInt(selectedOption.value) })
        });
        
        if (!response.ok) throw new Error('Failed to check answer');
        const result = await response.json();
        
        displayFeedback(result);
        updateProgress(result.correct);
        
        submitButton.classList.add('hidden');
        nextButton.classList.remove('hidden');
        recheckSection.classList.remove('hidden');
    } catch (error) {
        showError('Failed to submit answer: ' + error.message);
    }
}

// Display feedback for the answer
function displayFeedback(result) {
    feedbackSection.classList.remove('hidden');
    feedbackSection.className = `mt-4 p-4 rounded-lg ${result.correct ? 'bg-green-100' : 'bg-red-100'}`;
    feedbackSection.innerHTML = `
        <p class="font-semibold ${result.correct ? 'text-green-700' : 'text-red-700'}">
            ${result.correct ? 'Correct!' : 'Incorrect'}
        </p>
        <p class="mt-2">${result.explanation}</p>
    `;
}

// Update progress display
function updateProgress(correct) {
    questionsAnswered++;
    if (correct) score++;
    
    scoreElement.textContent = score;
    questionsAnsweredElement.textContent = questionsAnswered;
}

// Recheck question
async function recheckQuestion() {
    try {
        const response = await fetch(`/api/questions/${currentQuestion.id}/recheck`);
        if (!response.ok) throw new Error('Failed to recheck question');
        
        const result = await response.json();
        document.getElementById('newAnswerSection').classList.remove('hidden');
        document.getElementById('newAnswerContent').textContent = result.newAnswer;
    } catch (error) {
        showError('Failed to recheck question: ' + error.message);
    }
}

// Accept new answer
async function acceptNewAnswer() {
    try {
        await fetch(`/api/questions/${currentQuestion.id}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                answer: document.getElementById('newAnswerContent').textContent
            })
        });
        
        showSuccess('Answer updated successfully');
        document.getElementById('newAnswerSection').classList.add('hidden');
    } catch (error) {
        showError('Failed to update answer: ' + error.message);
    }
}

// Flag question
async function flagQuestion() {
    try {
        await fetch(`/api/questions/${currentQuestion.id}/flag`, {
            method: 'POST'
        });
        showSuccess('Question flagged for review');
    } catch (error) {
        showError('Failed to flag question: ' + error.message);
    }
}

// Delete question
async function deleteQuestion() {
    if (!confirm('Are you sure you want to delete this question?')) return;
    
    try {
        await fetch(`/api/questions/${currentQuestion.id}`, {
            method: 'DELETE'
        });
        showSuccess('Question deleted successfully');
        loadNextQuestion();
    } catch (error) {
        showError('Failed to delete question: ' + error.message);
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', initializePractice);
submitButton.addEventListener('click', submitAnswer);
nextButton.addEventListener('click', loadNextQuestion);
document.getElementById('recheckButton').addEventListener('click', recheckQuestion);
document.getElementById('acceptNewAnswer').addEventListener('click', acceptNewAnswer);
document.getElementById('rejectNewAnswer').addEventListener('click', () => {
    document.getElementById('newAnswerSection').classList.add('hidden');
});
document.getElementById('flagQuestion').addEventListener('click', flagQuestion);
document.getElementById('deleteQuestion').addEventListener('click', deleteQuestion);
