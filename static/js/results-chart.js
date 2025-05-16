// Results visualization using Chart.js
document.addEventListener('DOMContentLoaded', function() {
    // Score distribution chart
    const scoreChartCanvas = document.getElementById('score-distribution-chart');
    if (scoreChartCanvas) {
        const scoreDistributionData = JSON.parse(scoreChartCanvas.dataset.distribution || '{}');
        
        new Chart(scoreChartCanvas, {
            type: 'bar',
            data: {
                labels: Object.keys(scoreDistributionData),
                datasets: [{
                    label: 'Number of Students',
                    data: Object.values(scoreDistributionData),
                    backgroundColor: [
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(255, 159, 64, 0.7)',
                        'rgba(255, 205, 86, 0.7)',
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(54, 162, 235, 0.7)'
                    ],
                    borderColor: [
                        'rgb(255, 99, 132)',
                        'rgb(255, 159, 64)',
                        'rgb(255, 205, 86)',
                        'rgb(75, 192, 192)',
                        'rgb(54, 162, 235)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Score Distribution',
                        color: '#fff',
                        font: {
                            size: 16
                        }
                    },
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0,
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }
    
    // Student performance chart (individual results page)
    const performanceChartCanvas = document.getElementById('student-performance-chart');
    if (performanceChartCanvas) {
        const correctAnswers = parseInt(performanceChartCanvas.dataset.correct || '0');
        const incorrectAnswers = parseInt(performanceChartCanvas.dataset.incorrect || '0');
        const unanswered = parseInt(performanceChartCanvas.dataset.unanswered || '0');
        
        new Chart(performanceChartCanvas, {
            type: 'doughnut',
            data: {
                labels: ['Correct', 'Incorrect', 'Unanswered'],
                datasets: [{
                    data: [correctAnswers, incorrectAnswers, unanswered],
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.7)',
                        'rgba(255, 99, 132, 0.7)',
                        'rgba(201, 203, 207, 0.7)'
                    ],
                    borderColor: [
                        'rgb(75, 192, 192)',
                        'rgb(255, 99, 132)',
                        'rgb(201, 203, 207)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Question Results',
                        color: '#fff',
                        font: {
                            size: 16
                        }
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#fff'
                        }
                    }
                }
            }
        });
    }
    
    // Question difficulty chart (lecturer view)
    const difficultyChartCanvas = document.getElementById('question-difficulty-chart');
    if (difficultyChartCanvas) {
        const questionsData = JSON.parse(difficultyChartCanvas.dataset.questions || '[]');
        
        // Calculate success rate for each question
        const labels = [];
        const successRates = [];
        
        questionsData.forEach((question, index) => {
            labels.push(`Q${index + 1}`);
            const successRate = (question.correct_count / question.attempt_count) * 100 || 0;
            successRates.push(successRate.toFixed(1));
        });
        
        new Chart(difficultyChartCanvas, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Success Rate (%)',
                    data: successRates,
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgb(54, 162, 235)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Question Difficulty Analysis',
                        color: '#fff',
                        font: {
                            size: 16
                        }
                    },
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            afterLabel: function(context) {
                                const questionIndex = context.dataIndex;
                                const question = questionsData[questionIndex];
                                return [
                                    `Correct: ${question.correct_count}`,
                                    `Total: ${question.attempt_count}`
                                ];
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            },
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            color: '#fff'
                        },
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        }
                    }
                }
            }
        });
    }
});
