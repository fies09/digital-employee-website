async function submitAskForm() {
    // 获取表单中的textarea的值
    const resultText = document.getElementById('resultText').value;
    const chatData = document.getElementById('chat_data').value;
    const disData = document.getElementById('dis_data').value;
    const question = document.getElementById('question').value;
    const protocol = window.location.protocol;
    const hostname = window.location.hostname;
    const port = window.location.port;
    const playAudioButton = document.getElementById('playAudio');

    // 构建要发送的数据对象
    const data = {
        user_answer: resultText,
        chat_data: chatData ? JSON.parse(chatData) : {}, // 如果 chatData 为空则使用空对象
        dis_data: disData ? JSON.parse(disData) : {},   // 如果 disData 为空则使用空对象
        thrown_question: question ? JSON.parse(question) : {}
    };

    const apiEndpoint = `${protocol}//${hostname}:${port}/chat/demoAsk`;

    try {
        // 发送POST请求
        const response = await fetch(apiEndpoint, { // 替换为实际的API端点
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data) // 将JavaScript对象转换为JSON字符串
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const responseData = await response.json();
        console.log('Success:', responseData); // 处理成功响应的数据

        // 将返回的数据中的字段填入相应的textarea中
        if (responseData.question) {
            document.getElementById('textInput').value = responseData.question.doctor.statement;
            document.getElementById('question').value = JSON.stringify(responseData.question, null, 2);
            playAudioButton.click();
        }
        if (responseData.chat_data) {
            document.getElementById('chat_data').value = JSON.stringify(responseData.chat_data, null, 2);
        }
        if (responseData.dis_data) {
            document.getElementById('dis_data').value = JSON.stringify(responseData.dis_data, null, 2);
        }

    } catch (error) {
        console.error('Error:', error); // 处理错误
    }
}

function clearTextAreas() {
    const textAreas = document.querySelectorAll('textarea');
    textAreas.forEach(textarea => {
        textarea.value = '';
    });
}
