// Test creation functionality for lecturers
document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const addOptionBtn = document.getElementById('add-option');
    const optionsContainer = document.getElementById('options-container');
    const questionForm = document.getElementById('question-form');
    const questionTypeSelect = document.getElementById('question_type');
    const questionSelect = document.getElementById('question-select');
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.forEach(function (tooltipTriggerEl) {
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add option button click handler
    if (addOptionBtn && optionsContainer) {
        let optionCount = 0;
        
        addOptionBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            optionCount++;
            
            const optionRow = document.createElement('div');
            optionRow.className = 'row mb-3 option-row';
            optionRow.innerHTML = `
                <div class="col-md-9">
                    <input type="text" class="form-control option-text" placeholder="Option ${optionCount}" required>
                </div>
                <div class="col-md-2">
                    <div class="form-check mt-2">
                        <input type="radio" class="form-check-input is-correct" name="correct_option" id="correct_option_${optionCount}">
                        <label class="form-check-label" for="correct_option_${optionCount}">Correct</label>
                    </div>
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn btn-danger delete-option">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            `;
            
            optionsContainer.appendChild(optionRow);
            
            // Add event listener to delete button
            const deleteBtn = optionRow.querySelector('.delete-option');
            deleteBtn.addEventListener('click', function() {
                optionRow.remove();
            });
        });
    }
    
    // Question type change handler
    if (questionTypeSelect) {
        questionTypeSelect.addEventListener('change', function() {
            const optionsSection = document.getElementById('options-section');
            
            if (this.value === 'multiple_choice') {
                optionsSection.classList.remove('d-none');
            } else {
                optionsSection.classList.add('d-none');
            }
        });
    }
    
    // Question form submit handler
    if (questionForm) {
        questionForm.addEventListener('submit', function(e) {
            // If this is a multiple choice question, validate that options exist
            if (questionTypeSelect.value === 'multiple_choice') {
                const options = optionsContainer.querySelectorAll('.option-row');
                
                if (options.length < 2) {
                    e.preventDefault();
                    alert('Multiple choice questions must have at least 2 options.');
                    return;
                }
                
                // Check if a correct answer is selected
                const correctOptions = optionsContainer.querySelectorAll('.is-correct:checked');
                if (correctOptions.length === 0) {
                    e.preventDefault();
                    alert('Please mark at least one option as correct.');
                    return;
                }
            }
        });
    }
    
    // Save options to the server when a question is created
    document.addEventListener('question-created', function(e) {
        const questionId = e.detail.questionId;
        
        // Get all options
        const optionRows = optionsContainer.querySelectorAll('.option-row');
        const options = [];
        
        optionRows.forEach(row => {
            const optionText = row.querySelector('.option-text').value;
            const isCorrect = row.querySelector('.is-correct').checked;
            
            options.push({
                text: optionText,
                is_correct: isCorrect
            });
        });
        
        // Save each option via API
        options.forEach(option => {
            saveOption(questionId, option.text, option.is_correct);
        });
    });
    
    // Save an option to the server
    function saveOption(questionId, text, isCorrect) {
        fetch('/api/add-option', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                question_id: questionId,
                text: text,
                is_correct: isCorrect
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Option saved successfully');
            } else {
                console.error('Failed to save option');
            }
        })
        .catch(error => {
            console.error('Error saving option:', error);
        });
    }
    
    // Get CSRF token from meta tag
    function getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    }
    
    // Question select change handler
    if (questionSelect) {
        questionSelect.addEventListener('change', function() {
            const questionId = this.value;
            if (!questionId) return;
            
            // Load question details and options
            fetch(`/api/question/${questionId}`)
                .then(response => response.json())
                .then(data => {
                    // Populate form fields
                    document.getElementById('question_text').value = data.text;
                    document.getElementById('question_type').value = data.question_type;
                    document.getElementById('points').value = data.points;
                    
                    // Clear existing options
                    optionsContainer.innerHTML = '';
                    
                    // Add options if applicable
                    if (data.question_type === 'multiple_choice') {
                        document.getElementById('options-section').classList.remove('d-none');
                        
                        data.options.forEach((option, index) => {
                            const optionRow = document.createElement('div');
                            optionRow.className = 'row mb-3 option-row';
                            optionRow.dataset.optionId = option.id;
                            optionRow.innerHTML = `
                                <div class="col-md-9">
                                    <input type="text" class="form-control option-text" value="${option.text}" required>
                                </div>
                                <div class="col-md-2">
                                    <div class="form-check mt-2">
                                        <input type="radio" class="form-check-input is-correct" name="correct_option" id="correct_option_${index + 1}" ${option.is_correct ? 'checked' : ''}>
                                        <label class="form-check-label" for="correct_option_${index + 1}">Correct</label>
                                    </div>
                                </div>
                                <div class="col-md-1">
                                    <button type="button" class="btn btn-danger delete-option">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                            `;
                            
                            optionsContainer.appendChild(optionRow);
                            
                            // Add event listener to delete button
                            const deleteBtn = optionRow.querySelector('.delete-option');
                            deleteBtn.addEventListener('click', function() {
                                optionRow.remove();
                            });
                        });
                    } else {
                        document.getElementById('options-section').classList.add('d-none');
                    }
                    
                    // Update form action to update rather than create
                    questionForm.action = `/lecturer/update-question/${questionId}`;
                    document.getElementById('submit-btn').textContent = 'Update Question';
                })
                .catch(error => {
                    console.error('Error loading question:', error);
                });
        });
    }
});
