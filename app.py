from flask import Flask, render_template, request, jsonify, session
import json
import os
import time
import threading
from dotenv import load_dotenv
from agents import process_query

from uuid import uuid4

load_dotenv()

app = Flask(__name__)

app.secret_key = str(uuid4())

# 导入数据库模块
from database import create_tables, log_conversation, get_all_conversations, get_conversation_history, delete_conversation

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        start_time = time.time()
        
        data = request.get_json()
        user_question = data.get('question', '') or data.get('query', '') or data.get('user_question', '')
        
        if not user_question:
            return jsonify({'reply': 'Please enter your question'})
        
        if 'conversation_history' not in session:
            session['conversation_history'] = []
            session['user_id'] = str(uuid4())
        
        session['conversation_history'].append({
            'role': 'user',
            'content': user_question
        })

        result = process_query(user_question, session['conversation_history'], session['user_id'], session.get('last_recommendations'))

        session['conversation_history'].append({
            'role': 'assistant',
            'content': result['reply']
        })

        # 记录对话到数据库
        log_conversation(session['user_id'], 'user', user_question, session['user_id'])
        log_conversation(session['user_id'], 'assistant', result['reply'], session['user_id'])

        session['last_recommendations'] = [p['id'] for p in result.get('products', [])]
        
        if len(session['conversation_history']) > 40:
            session['conversation_history'] = session['conversation_history'][-40:]
        
        response_time = time.time() - start_time

        success = result['reply'] != "Sorry, an error occurred while processing your request. Please try again later."
        
        return jsonify({
            'reply': result['reply'],
            'conversation_id': session['user_id'],
            'products': result.get('products', [])
        })
        
    except Exception as e:
        print(f"API error: {e}")
        return jsonify({'reply': 'Sorry, an error occurred while processing your request. Please try again later.'})

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    conversations = get_all_conversations()
    return jsonify(conversations)

@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    history = get_conversation_history(conversation_id)
    return jsonify(history)

@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation_api(conversation_id):
    success = delete_conversation(conversation_id)
    if success:
        return jsonify({'message': 'Conversation deleted successfully'})
    else:
        return jsonify({'error': 'Failed to delete conversation'}), 500

if __name__ == '__main__':
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # 初始化数据库表
    create_tables()
    
    app.run(debug=True, host='0.0.0.0', port=3000)