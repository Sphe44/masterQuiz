// Face detection module using face-api.js
const FaceDetection = (function() {
    // Private variables
    let videoElement;
    let canvas;
    let detectionInterval;
    let attemptId;
    let faceApiLoaded = false;
    let isMonitoring = false;
    let lastDetectionStatus = '';
    let loginToken = '';

    // Face API models path
    const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model/';
    
    // Initialize the module
    async function init(videoElementId, canvasElementId, testAttemptId, token) {
        console.log('Initializing face detection...');
        
        // Store the token
        loginToken = token;
        
        // Store attempt ID
        attemptId = testAttemptId;
        
        // Get DOM elements
        videoElement = document.getElementById(videoElementId);
        canvas = document.getElementById(canvasElementId);
        
        if (!videoElement || !canvas) {
            console.error('Video or canvas element not found');
            return false;
        }
        
        // Check if face-api is available
        if (!window.faceapi) {
            console.error('Face API not loaded');
            return false;
        }
        
        try {
            // Load models
            await loadModels();
            console.log('Face detection models loaded');
            faceApiLoaded = true;
            
            // Setup video stream
            return await setupCamera();
        } catch (error) {
            console.error('Error initializing face detection:', error);
            return false;
        }
    }
    
    // Load required models
    async function loadModels() {
        await Promise.all([
            faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
            faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
            faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL)
        ]);
    }
    
    // Setup camera stream
    async function setupCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480 },
                audio: false
            });
            
            videoElement.srcObject = stream;
            
            return new Promise((resolve) => {
                videoElement.onloadedmetadata = () => {
                    // Adjust canvas size to match video
                    canvas.width = videoElement.videoWidth;
                    canvas.height = videoElement.videoHeight;
                    resolve(true);
                };
            });
        } catch (error) {
            console.error('Error accessing webcam:', error);
            logFaceDetection('camera_error', 'Failed to access webcam');
            return false;
        }
    }
    
    // Start face monitoring
    function startMonitoring(intervalMs = 2000) {
        if (!faceApiLoaded || isMonitoring) return;
        
        isMonitoring = true;
        
        // Initial detection
        detectFace();
        
        // Set interval for continuous detection
        detectionInterval = setInterval(detectFace, intervalMs);
        
        return true;
    }
    
    // Stop face monitoring
    function stopMonitoring() {
        if (detectionInterval) {
            clearInterval(detectionInterval);
            detectionInterval = null;
        }
        isMonitoring = false;
    }
    
    // Detect faces in the video stream
    async function detectFace() {
        if (!videoElement || !videoElement.readyState || videoElement.readyState < 2) {
            return;
        }
        
        try {
            // Detect faces
            const detections = await faceapi.detectAllFaces(
                videoElement, 
                new faceapi.TinyFaceDetectorOptions()
            ).withFaceLandmarks();
            
            // Draw results on canvas
            const context = canvas.getContext('2d');
            context.clearRect(0, 0, canvas.width, canvas.height);
            
            if (detections.length === 0) {
                // No face detected
                logFaceDetection('no_face', 'No face detected');
            } else if (detections.length === 1) {
                // One face detected (normal case)
                faceapi.draw.drawDetections(canvas, detections);
                faceapi.draw.drawFaceLandmarks(canvas, detections);
                logFaceDetection('face_detected', 'Face detected');
            } else {
                // Multiple faces detected (potential cheating)
                faceapi.draw.drawDetections(canvas, detections);
                faceapi.draw.drawFaceLandmarks(canvas, detections);
                logFaceDetection('multiple_faces', `${detections.length} faces detected`);
            }
        } catch (error) {
            console.error('Error during face detection:', error);
            logFaceDetection('detection_error', 'Error during face detection');
        }
    }
    
    // Log face detection status to the server
    function logFaceDetection(status, details) {
        // Only log if status changed to avoid flooding server
        if (status === lastDetectionStatus) return;
        
        lastDetectionStatus = status;
        
        // Update UI indicators
        const statusElement = document.getElementById('face-detection-status');
        if (statusElement) {
            statusElement.innerText = status.replace('_', ' ').toUpperCase();
            
            // Add appropriate classes based on status
            statusElement.className = 'badge';
            if (status === 'face_detected') {
                statusElement.classList.add('bg-success');
            } else if (status === 'no_face' || status === 'multiple_faces') {
                statusElement.classList.add('bg-danger');
            } else {
                statusElement.classList.add('bg-warning');
            }
        }
        
        // Send log to server
        if (attemptId) {
            fetch('/api/face-log', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${loginToken}`
                },
                body: JSON.stringify({
                    attempt_id: attemptId,
                    status: status,
                    details: details
                })
            }).catch(error => {
                console.error('Error logging face detection:', error);
            });
        }
    }
    
    // Public API
    return {
        init,
        startMonitoring,
        stopMonitoring
    };
})();
