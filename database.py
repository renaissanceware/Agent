import mysql.connector
from mysql.connector import Error
import datetime
import uuid
import json

def create_connection():
    """
    创建MySQL数据库连接
    """
    try:
        connection = mysql.connector.connect(
            host='sjc1.clusters.zeabur.com',
            port=27888,
            user='root',
            password='2hKk0nzQ7lM9TZE3LOo6ay54fw18GvXS',
            database='zeabur'
        )
        if connection.is_connected():
            print('Connected to MySQL database')
            return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
    return None

def create_tables():
    """
    创建必要的数据库表
    """
    connection = create_connection()
    if connection is None:
        print("Connection is None, cannot create tables")
        return False
    
    try:
        cursor = connection.cursor()
        print("Cursor created successfully")
        
        # 创建conversations表
        create_conversations_table = """
        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            last_message TEXT
        )
        """
        print("Executing create conversations table")
        cursor.execute(create_conversations_table)
        print("Conversations table created or exists")
        
        # 创建messages表
        create_messages_table = """
        CREATE TABLE IF NOT EXISTS messages (
            message_id VARCHAR(36) PRIMARY KEY,
            conversation_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            role ENUM('user', 'assistant') NOT NULL,
            content TEXT NOT NULL,
            products JSON,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
        )
        """
        print("Executing create messages table")
        cursor.execute(create_messages_table)
        print("Messages table created or exists")
        
        connection.commit()
        print('Tables created successfully')
        return True
    except Error as e:
        print(f"Error creating tables: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("Connection closed")

def log_conversation(user_id, role, content, conversation_id=None, products=None):
    """
    记录对话消息到数据库
    """
    connection = create_connection()
    if connection is None:
        return False
    
    try:
        cursor = connection.cursor()
        
        # 如果没有提供conversation_id，使用user_id作为conversation_id
        if not conversation_id:
            conversation_id = user_id
        
        # 检查conversation_id是否存在
        check_conversation = "SELECT conversation_id FROM conversations WHERE conversation_id = %s"
        cursor.execute(check_conversation, (conversation_id,))
        if not cursor.fetchone():
            # 创建新的对话记录
            insert_conversation = """
            INSERT INTO conversations (conversation_id, user_id, last_message)
            VALUES (%s, %s, %s)
            """
            cursor.execute(insert_conversation, (conversation_id, user_id, content))
        else:
            # 更新对话的最后消息
            update_conversation = """
            UPDATE conversations
            SET last_message = %s, updated_at = CURRENT_TIMESTAMP
            WHERE conversation_id = %s
            """
            cursor.execute(update_conversation, (content, conversation_id))
        
        # 创建消息记录
        message_id = str(uuid.uuid4())
        
        # 将products转换为JSON字符串
        products_json = json.dumps(products) if products else None
        
        insert_message = """
        INSERT INTO messages (message_id, conversation_id, user_id, role, content, products)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_message, (message_id, conversation_id, user_id, role, content, products_json))
        
        connection.commit()
        return True
    except Error as e:
        print(f"Error logging conversation: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def get_all_conversations():
    """
    获取所有对话
    """
    connection = create_connection()
    if connection is None:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        get_conversations = """
        SELECT conversation_id, user_id, created_at, updated_at, last_message
        FROM conversations
        ORDER BY updated_at DESC
        """
        cursor.execute(get_conversations)
        conversations = cursor.fetchall()
        
        return conversations
    except Error as e:
        print(f"Error getting conversations: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def get_conversation_history(conversation_id):
    """
    获取特定对话的历史消息
    """
    connection = create_connection()
    if connection is None:
        return []
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        get_messages = """
        SELECT message_id, conversation_id, user_id, role, content, products, created_at
        FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at ASC, role ASC
        """
        cursor.execute(get_messages, (conversation_id,))
        messages = cursor.fetchall()
        
        # 将JSON字符串转换为Python对象
        for msg in messages:
            if msg.get('products'):
                try:
                    msg['products'] = json.loads(msg['products'])
                except (json.JSONDecodeError, TypeError):
                    msg['products'] = None
            else:
                msg['products'] = None
        
        return messages
    except Error as e:
        print(f"Error getting conversation history: {e}")
        return []
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

def delete_conversation(conversation_id):
    """
    删除对话及其所有消息
    """
    connection = create_connection()
    if connection is None:
        return False
    
    try:
        cursor = connection.cursor()
        
        delete_query = "DELETE FROM conversations WHERE conversation_id = %s"
        cursor.execute(delete_query, (conversation_id,))
        connection.commit()
        
        return True
    except Error as e:
        print(f"Error deleting conversation: {e}")
        return False
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
