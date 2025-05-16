// Test-taking functionality
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const testForm = document.getElementById('test-form');
    const submitTestBtn = document.getElementById('submit-test');
    const timerDisplay = document.getElementById('timer-display');
    const questionNavigation = document.getElementById('question-navigation');
    
    // Data attributes
    const attemptId = testForm ? testForm.dataset.attemptId : null;
    const remainingSeconds = testForm ? parseInt(testForm.dataset.remainingSeconds) : 0;
    const tokenElement = document.getElementById('api-token');
    const token = tokenElement ? tokenElement.value : null;
    
    let countdown;
    let answers = {};
    
    // Initialize face detection if available
    if (typeof FaceDetection !== 'undefined' && attemptId && token) {
        FaceDetection.init('webcam-video', 'detection-canvas', attemptId, token)
            .then(success => {
                if (success) {
                    FaceDetection.startMonitoring();
                    console.log('Face detection monitoring started');
                } else {
                    console.error('Failed to initialize face detection');
                    showAlert('Warning: Face detection could not be initialized. Your test activity may be flagged.', 'warning');
                }
            });
    }
    
    // Initialize timer if available
    if (timerDisplay && remainingSeconds > 0) {
        startTimer(remainingSeconds);
    }
    
    // Set up tab visibility detection
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'hidden') {
            logTabSwitch();
        }
    });
    
    // Set up answer auto-save
    if (testForm) {
        const radioInputs = testForm.querySelectorAll('input[type="radio"]');
        radioInputs.forEach(input => {
            input.addEventListener('change', function() {
                saveAnswer(this.name, this.value);
            });
        });
    }
    
    // Set up question navigation
    if (questionNavigation) {
        const questionButtons = questionNavigation.querySelectorAll('.question-btn');
        questionButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const questionId = this.dataset.questionId;
                const targetQuestion = document.querySelector(`#question-${questionId}`);
                
                // Hide all questions
                document.querySelectorAll('.question-container').forEach(q => {
                    q.classList.add('d-none');
                });
                
                // Show target question
                targetQuestion.classList.remove('d-none');
                
                // Update active state in navigation
                questionNavigation.querySelectorAll('.question-link').forEach(l => {
                    l.classList.remove('active');
                });
                this.classList.add('active');
            });
        });
        
        // Show the first question by default
        if (questionButtons.length > 0) {
            const firstQuestion = document.querySelector('.question-container');
            if (firstQuestion) {
                firstQuestion.classList.add('active');
            }
            questionButtons[0].classList.add('active');
        }
    }
    
    // Handle question navigation
    if (questionNavigation) {
        const questionButtons = questionNavigation.querySelectorAll('.question-btn');
        const questions = document.querySelectorAll('.question-container');
        
        questionButtons.forEach((button, index) => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                // Hide all questions and remove active class from buttons
                questions.forEach(q => q.classList.remove('active'));
                questionButtons.forEach(b => b.classList.remove('active'));
                
                // Show selected question and mark button as active
                questions[index].classList.add('active');
                button.classList.add('active');
            });
        });
    }
    
    // Submit test button
    if (submitTestBtn) {
        submitTestBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Confirm before submitting
            if (confirm('Are you sure you want to submit this test? You cannot change your answers after submission.')) {
                submitTest();
            }
        });
    }
    
    // Start countdown timer
    function startTimer(seconds) {
        let remainingTime = seconds;
        
        updateTimerDisplay(remainingTime);
        
        countdown = setInterval(function() {
            remainingTime--;
            updateTimerDisplay(remainingTime);
            
            if (remainingTime <= 0) {
                clearInterval(countdown);
                alert('Time is up! Your test will be submitted automatically.');
                submitTest();
            }
        }, 1000);
    }
    
    // Update timer display
    function updateTimerDisplay(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        
        timerDisplay.textContent = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        
        // Change color when low on time
        if (seconds < 300) { // less than 5 minutes
            timerDisplay.classList.add('text-danger');
        }
    }
    
    // Save an answer via API
    function saveAnswer(questionId, optionId) {
        // Extract actual IDs from the input name (format: "question-{id}")
        const qId = questionId.split('-')[1];
        
        // Store answer locally
        answers[qId] = optionId;
        
        // Mark question as answered in navigation
        const navLink = document.querySelector(`.question-link[data-question-id="${qId}"]`);
        if (navLink) {
            navLink.classList.add('answered');
        }
        
        // For debugging
        console.log(`Saving answer - Question ID: ${qId}, Option ID: ${optionId}, Token: ${token ? 'Present' : 'Missing'}, Attempt ID: ${attemptId}`);
        
        // Send to server
        fetch('/api/submit-answer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                attempt_id: parseInt(attemptId),
                question_id: parseInt(qId),
                selected_option_id: parseInt(optionId)
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.error || 'Server error');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                console.log('Answer saved successfully');
            } else {
                throw new Error('Failed to save answer');
            }
        })
        .catch(error => {
            console.error('Error saving answer:', error.message);
            showAlert(`There was a problem saving your answer: ${error.message}. Please try again.`, 'danger');
        });
    }
    
    // Submit the entire test
    function submitTest() {
        // Stop timer if running
        if (countdown) {
            clearInterval(countdown);
        }
        
        // Stop face detection
        if (typeof FaceDetection !== 'undefined') {
            FaceDetection.stopMonitoring();
        }
        
        // Disable submit button
        if (submitTestBtn) {
            submitTestBtn.disabled = true;
            submitTestBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...';
        }
        
        // For debugging
        console.log(`Submitting test - Attempt ID: ${attemptId}, Token: ${token ? 'Present' : 'Missing'}`);
        
        // Submit to server
        fetch('/api/submit-test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                attempt_id: parseInt(attemptId)
            })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    throw new Error(errorData.error || 'Server error');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Show score and redirect
                alert(`Test submitted successfully! Your score: ${data.score.toFixed(2)}%`);
                window.location.href = data.result_url;
            } else {
                throw new Error('Failed to submit test');
            }
        })
        .catch(error => {
            console.error('Error submitting test:', error.message);
            showAlert(`There was a problem submitting your test: ${error.message}. Please try again.`, 'danger');
            
            // Re-enable submit button
            if (submitTestBtn) {
                submitTestBtn.disabled = false;
                submitTestBtn.textContent = 'Submit Test';
            }
        });
    }
    
    // Log tab switch event
    function logTabSwitch() {
        if (!attemptId || !token) return;
        
        fetch('/api/face-log', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                attempt_id: parseInt(attemptId),
                status: 'tab_switch',
                details: 'User switched tabs or minimized window'
            })
        }).catch(error => {
            console.error('Error logging tab switch:', error);
        });
    }
    
    // Show alert message
    function showAlert(message, type) {
        const alertContainer = document.getElementById('alert-container');
        if (!alertContainer) return;
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        alertContainer.appendChild(alert);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 150);
        }, 5000);
    }
    
    // We're now using the token directly from the template
    // No need for login functionality
});
