function submitText() {
    const textInput = document.getElementById('textInput').value;
    const audioPlayer = document.getElementById('audioPlayer');

    // Prepare the request data
    const requestData = {
        text: textInput,
        format: 'mp3',  // Assuming backend supports MP3; adjust as needed
        sampleRate: 16000  // Sample rate as required by backend
    };
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port;
    const apiEndpoint = `${protocol}//${hostname}:${port}/audio/tts`;
    // Send the request to your TTS endpoint
    fetch(apiEndpoint, {  // Change this URL to match your actual API endpoint
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.blob())  // Assume the server responds with a blob (audio file)
    .then(blob => {
        const audioUrl = URL.createObjectURL(blob);
        audioPlayer.src = audioUrl;
        audioPlayer.hidden = false;
        audioPlayer.play();
    })
    .catch(error => {
        console.error('Error fetching the TTS audio:', error);
        alert('Failed to fetch TTS audio.');
    });
}
