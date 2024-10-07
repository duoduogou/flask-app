# app.py

import sys
import os
import json
import re
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from filelock import FileLock, Timeout
import threading
import time

# 设置输出编码为 UTF-8，防止输出中文时出错
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf8', buffering=1)

app = Flask(__name__, static_folder='static')

# 设置固定的 secret_key（请将 'your_fixed_secret_key' 替换为您的实际密钥）
app.secret_key = 'your_fixed_secret_key'

CORS(app)  # 仅用于本地开发，生产环境请移除

# 问题列表
questions = [
    {"question": "请问您有多少年相关工作经验？", "options": ["0-1年", "2-4年", "5年以上"]},
    {"question": "您有Python开发经验吗？", "options": ["是", "否"]},
    {"question": "您有项目管理经验吗？", "options": ["是", "否"]},
    {"question": "请描述您的专业水平：", "options": ["初级", "中级", "高级"]},
    {"question": "您是否曾在团队中工作过？", "options": ["是", "否"]},
    {"question": "您熟悉敏捷开发方法吗？", "options": ["是", "否"]},
    {"question": "您能在紧急期限下工作吗？", "options": ["是", "否"]},
    {"question": "您的期望薪资是多少？", "options": ["低于50K", "50K-70K", "高于70K"]},
    {"question": "您可以立即开始工作吗？", "options": ["是", "否"]}
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_message = request.json.get("message")

        # 检查 user_message 是否为 None
        if user_message is None:
            reply = "您好！欢迎参加我们的职位申请。请问您的名字是什么？（至少两个字符）"
            session['stage'] = 'start'
            session['candidate_info'] = {}
            session['candidate_answers'] = []
            return jsonify({"reply": reply})

        reply = ""

        if 'stage' not in session:
            session['stage'] = 'start'
            session['candidate_info'] = {}
            session['candidate_answers'] = []
            reply = "您好！欢迎参加我们的职位申请。让我们先了解一下您的个人信息。请问您的名字是什么？（至少两个字符）"
            return jsonify({"reply": reply})

        stage = session['stage']
        candidate_info = session['candidate_info']
        candidate_answers = session['candidate_answers']

        if stage == 'start':
            # 收集名字
            if not re.match(r'^[\u4e00-\u9fa5a-zA-Z]{2,}$', user_message):
                reply = "抱歉，您的名字似乎不符合要求。请确保您的名字至少包含两个字符，例如“张三”。请重新输入您的名字："
            else:
                candidate_info['name'] = user_message
                session['stage'] = 'collect_email'
                session['candidate_info'] = candidate_info
                reply = "请提供您的电子邮箱地址："
            return jsonify({"reply": reply})

        elif stage == 'collect_email':
            # 验证电子邮箱
            if not re.match(r'^[^@]+@[^@]+\.[^@]+$', user_message):
                reply = "电子邮箱格式不正确，例如 example@example.com，请重新输入："
            else:
                candidate_info['email'] = user_message
                session['stage'] = 'collect_phone'
                session['candidate_info'] = candidate_info
                reply = "请提供您的手机号码（11位数字）："
            return jsonify({"reply": reply})

        elif stage == 'collect_phone':
            # 验证手机号码
            if not re.match(r'^\d{11}$', user_message):
                reply = "手机号码格式不正确，应为11位数字，例如13800138000，请重新输入："
            else:
                candidate_info['phone'] = user_message
                session['stage'] = 'ask_questions'
                session['question_index'] = 0
                session['candidate_info'] = candidate_info
                # 开始提问
                question = questions[0]['question']
                options = questions[0]['options']
                reply = f"{question}\n选项：{', '.join(options)}"
            return jsonify({"reply": reply})

        elif stage == 'ask_questions':
            # 收集问题的答案
            index = session.get('question_index', 0)
            if index >= len(questions):
                # 所有问题回答完毕
                session['stage'] = 'finished'
                save_candidate_info(candidate_info, candidate_answers)
                threading.Thread(target=send_email_after_redirect, args=(candidate_info,)).start()  # 异步发送邮件
                return jsonify({"reply": "非常感谢您的回答！请等待，我们正在处理您的请求...", "disable_input": True, "redirect": url_for('thank_you')})

            current_question = questions[index]
            options = current_question['options']
            if user_message not in options:
                reply = f"抱歉，请从以下选项中选择：{', '.join(options)}"
            else:
                candidate_answers.append({"question": current_question['question'], "answer": user_message})
                session['candidate_answers'] = candidate_answers
                index += 1
                if index < len(questions):
                    session['question_index'] = index
                    next_question = questions[index]
                    reply = f"{next_question['question']}\n选项：{', '.join(next_question['options'])}"
                else:
                    session['stage'] = 'finished'
                    save_candidate_info(candidate_info, candidate_answers)
                    threading.Thread(target=send_email_after_redirect, args=(candidate_info,)).start()  # 异步发送邮件
                    return jsonify({"reply": "非常感谢您的回答！请等待，我们正在处理您的请求...", "disable_input": True, "redirect": url_for('thank_you')})
            return jsonify({"reply": reply})

        else:
            reply = "抱歉，我没有理解您的回复。"
            return jsonify({"reply": reply})

    except Exception as e:
        print(f"聊天路由出错：{e}")
        return jsonify({"reply": "处理您的请求时出错，请稍后再试。"}), 500

@app.route('/thank_you')
def thank_you():
    candidate_info = session.get('candidate_info', {})
    email = candidate_info.get('email', '未提供')
    return render_template('thank_you.html', message=f"感谢您的耐心等待！邮件已发送到 {email}，请查收。")

def send_email_after_redirect(candidate_info):
    try:
        time.sleep(5)  # 模拟一些处理时间
        send_email(candidate_info)
    except Exception as e:
        print(f"跳转后发送邮件失败：{e}")

def save_candidate_info(candidate_info, candidate_answers):
    data = {
        "id": get_next_candidate_id(),
        "name": candidate_info['name'],
        "email": candidate_info['email'],
        "phone": candidate_info['phone'],
        "answers": candidate_answers
    }
    lock_file = 'candidate_data.lock'
    data_file = 'candidate_data.json'
    try:
        lock = FileLock(lock_file, timeout=10)
        with lock:
            if not os.path.exists(data_file):
                existing_data = []
            else:
                with open(data_file, 'r', encoding='utf-8') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        existing_data = []
            existing_data.append(data)
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=4)
        print(f"候选人信息已保存到 {data_file}")
    except Timeout:
        print("无法获取保存候选人信息的锁。")
        raise

def get_next_candidate_id():
    data_file = 'candidate_data.json'
    if not os.path.exists(data_file):
        return 1
    with open(data_file, 'r', encoding='utf-8') as f:
        try:
            existing_data = json.load(f)
            return len(existing_data) + 1
        except json.JSONDecodeError:
            return 1

def send_email(candidate_info):
    smtp_server = "smtp-relay.brevo.com"
    smtp_port = 587
    smtp_login = "7d67b9001@smtp-brevo.com"
    smtp_password = "PZtdYCj2DqbT6IaA"

    sender_email = "dododogdododogdodo@gmail.com"
    receiver_email = candidate_info['email']
    subject = "面试邀请"
    body = f"尊敬的 {candidate_info['name']}，\n\n恭喜您通过了初步筛选。我们诚邀您参加面对面的面试。\n\n此致\n人力资源团队"

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_login, smtp_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()

        print("邮件发送成功！")
    except Exception as e:
        print(f"邮件发送失败：{e}")

if __name__ == '__main__':
    app.run(debug=True)


