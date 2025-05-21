function uploadAudio() {
    const form = document.getElementById('uploadForm');
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return;
    }
    const formData = new FormData(form);
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port;
    const formatSelect = document.getElementById('format');
    const selectedFormat = formatSelect.value;

    // Alert user about the conversion time for specific formats
    if (selectedFormat === 'webm') {
        showToast('WEBM格式的音频需要转换后才能识别，请耐心等待。。。', 'info');
    }
    // Construct the API endpoint
    const apiEndpoint = `${protocol}//${hostname}:${port}/audio/asr`;

    fetch(apiEndpoint, {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
        // Check if the result field exists and update the text area
        if (data.result) {
            document.getElementById('resultText').value = data.result;
        } else {
            document.getElementById('resultText').value = "没能转换出东西来。。。";
        }
        showToast('音频文件上传成功！', 'info');
        console.log('音频文件上传成功！');
    })
    .catch((error) => {
        console.error('Error:', error);
        showToast('音频文件上传失败！', 'error');
        document.getElementById('resultText').value = "处理音频失败！";
    });
}
function checkFileType() {
    const fileInput = document.getElementById('audio_file');
    const file = fileInput.files[0];

    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
        const arr = (new Uint8Array(e.target.result)).subarray(0, 4);
        let header = "";
        for (let i = 0; i < arr.length; i++) {
            header += arr[i].toString(16).padStart(2, '0');
        }

        console.log("File header:", header);
        const format = determineFormat(header);
        console.log("Detected format:", format);

        // Set the format in your form, or handle unknown format
        const formatSelect = document.getElementById('format');
        if (format) {
            formatSelect.value = format;
        } else {
            alert('未能识别出您上传的文件格式，请手动选择格式或换一个文件上传');
            formatSelect.value = ''; // reset or set to a default value
        }
    };

        // Read the first 4 bytes of the file
        reader.readAsArrayBuffer(file.slice(0, 4));
    }

function determineFormat(header) {
    // Map of audio signatures to formats
    const formats = {
        '1a45dfa3': 'webm',    // EBML, typical for WebM files
        '4f676753': 'opus',  // OggS, common for OPUS
        '52494646': 'wav',   // RIFF, could be WAV
        'fff1': 'aac',       // AAC ADTS
        'fff9': 'aac',       // AAC ADTS
        '494433': 'mp3',     // ID3, could be MP3
        'fff3': 'mp3',       // MP3 with MPEG 2.5 extension
        // More headers can be added here
    };

    for (let signature in formats) {
        if (header.startsWith(signature)) {
            return formats[signature];
        }
    }
    return null; // or 'unknown' if you have an 'unknown' option in your dropdown
}

let mediaRecorder;
let audioChunks = [];
let recordingTimeout;

document.addEventListener('DOMContentLoaded', function() {
    const startButton = document.getElementById('startRecording');
    const stopButton = document.getElementById('stopRecording');

    startButton.addEventListener('click', startRecording);
    stopButton.addEventListener('click', stopRecording);
});

async function startRecording() {
    document.getElementById('audioPlayback').hidden = true;
    document.getElementById('recordingStatus').style.display = 'block';
    document.getElementById('stopRecording').disabled = false;
    document.getElementById('startRecording').disabled = true;

    const formatSelect = document.getElementById('format');
    formatSelect.value = 'webm';
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showToast('浏览器不支持录音。', 'error');
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const options = { mimeType: 'audio/webm; codecs=opus' };
        if (MediaRecorder.isTypeSupported(options.mimeType)) {
            mediaRecorder = new MediaRecorder(stream, options);
        } else {
            console.error('Unsupported MIME type:', options.mimeType);
            showToast('不支持的 MIME 类型: ' + options.mimeType, 'error');
            document.getElementById('stopRecording').disabled = true;
            document.getElementById('startRecording').disabled = false;
            return;
        }

        mediaRecorder.start();

        recordingTimeout = setTimeout(() => {
            if (mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
        }, 59000); // Stops recording after 59 seconds

        mediaRecorder.ondataavailable = function(event) {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = function() {
            clearTimeout(recordingTimeout); // Clear the timeout
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = document.getElementById('audioPlayback');
            audio.src = audioUrl;
            audio.hidden = false;
            const audioInput = document.getElementById('audio_file');
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(new File([audioBlob], "recording.webm", {type: "audio/webm"}));
            audioInput.files = dataTransfer.files;
            audioChunks = [];
        };
    } catch (error) {
        console.error('未能访问麦克风:', error);
        showToast('未能访问麦克风: ' + error.message, 'error');
        document.getElementById('stopRecording').disabled = true;
        document.getElementById('startRecording').disabled = false;
    }
}

function stopRecording() {
    const uploadRecording = document.getElementById('uploadRecording');
    showToast('录音已停止，两秒后自动上传。。。', 'info');
    document.getElementById('recordingStatus').style.display = 'none';
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        document.getElementById('stopRecording').disabled = true;
        document.getElementById('startRecording').disabled = false;
    }

    setTimeout(() => {
        uploadRecording.click();
    }, 2000); // 2000 毫秒等于 2 秒
}

function showToast(message, type = 'info') {
    const toastElement = document.getElementById('liveToast');
    const toastBody = toastElement.querySelector('.toast-body');
    const header = toastElement.querySelector('.toast-header');

    // Set the message and header color based on the type of message
    toastBody.textContent = message;
    if (type === 'error') {
        header.style.backgroundColor = 'red';
        header.style.color = 'white';
    } else {
        header.style.backgroundColor = 'green';
        header.style.color = 'white';
    }

    const toast = new bootstrap.Toast(toastElement); // Initialize the toast
    toast.show(); // Show the toast
}
