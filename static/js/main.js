// static/js/main.js

let chatStarted = false;  // 标志变量，表示聊天是否已经开始

function startChat() {
    if (!chatStarted) {  // 仅在聊天未开始时执行一次
        chatStarted = true;  // 将标志变量设置为 true，表示聊天已经开始
        console.log('startChat 被触发');
        // 发送初始消息到服务器
        sendInitialMessage();
        // 移除事件监听器，防止重复触发
        document.removeEventListener('keydown', startChat);
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            chatContainer.removeEventListener('click', startChat);
        }
    }
}

function sendInitialMessage() {
    fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: null }),  // 发送初始请求，无需用户输入
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        processServerReply(data.reply);
    })
    .catch(error => {
        console.error('Error occurred during fetch:', error);
        addMessageToChatBox('处理您的请求时出错，请检查您的网络连接并稍后重试。', 'bot');
    });
}

function sendMessage(message = null) {
    let userMessage;

    if (message) {
        userMessage = message;
    } else {
        const userInput = document.getElementById('user-input');
        userMessage = userInput.value.trim();
    }

    if (userMessage) {
        if (!message) {
            addMessageToChatBox(userMessage, 'user');
            document.getElementById('user-input').value = '';
        }

        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: userMessage }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.redirect) {
                // 显示请等待信息，然后禁用输入框
                addMessageToChatBox('请等待，我们正在处理您的请求...', 'bot');
                toggleUserInput(false);
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 2000);  // 2秒后跳转页面
            } else {
                processServerReply(data.reply);
            }
        })
        .catch(error => {
            console.error('Error occurred during fetch:', error);
            addMessageToChatBox('处理您的请求时出错，请检查您的网络连接并稍后重试。', 'bot');
        });
    }
}

function processServerReply(reply) {
    addMessageToChatBox(reply, 'bot');
    const optionsMatch = reply.match(/选项：(.+)/);
    if (optionsMatch) {
        const optionsText = optionsMatch[1];
        const options = optionsText.split(/, */);
        showOptions(options);
    } else {
        hideOptions();
    }
}

function addMessageToChatBox(message, sender) {
    const chatBox = document.getElementById('chat-box');
    const messageElement = document.createElement('div');
    messageElement.textContent = message;
    messageElement.classList.add('chat-message', sender);
    chatBox.appendChild(messageElement);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function toggleUserInput(showInput) {
    const inputContainer = document.getElementById('input-container');
    const optionsContainer = document.getElementById('options-container');

    if (showInput) {
        inputContainer.style.display = 'flex';
        optionsContainer.style.display = 'none';
    } else {
        inputContainer.style.display = 'none';
        optionsContainer.style.display = 'flex';
    }
}

function showOptions(options) {
    const optionsContainer = document.getElementById('options-container');
    optionsContainer.innerHTML = '';
    options.forEach(option => {
        const button = document.createElement('button');
        button.textContent = option;
        button.classList.add('option-button');
        button.addEventListener('click', () => {
            sendMessage(option);
            hideOptions();
        });
        optionsContainer.appendChild(button);
    });
    toggleUserInput(false);
}

function hideOptions() {
    const optionsContainer = document.getElementById('options-container');
    optionsContainer.innerHTML = '';
    toggleUserInput(true);
}

// 页面加载时等待任意键或鼠标点击开始聊天
window.onload = function() {
    addMessageToChatBox('您好！欢迎参加我们的职位申请。请按任意键或点击页面开始...', 'bot');
    console.log('页面加载完成，添加事件监听器');

    // 使用 'keydown' 代替 'keypress'
    document.addEventListener('keydown', startChat);

    const chatContainer = document.getElementById('chat-container');
    if (chatContainer) {
        chatContainer.addEventListener('click', startChat);
    } else {
        console.error('找不到ID为 "chat-container" 的元素');
    }

    const userInput = document.getElementById('user-input');
    if (userInput) {
        userInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        });
    } else {
        console.error('找不到ID为 "user-input" 的元素');
    }
};
