import os
import json
import requests
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from recommendation_engine import RecommendationEngine, get_recommendation_engine

load_dotenv()

class Agent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.api_base = os.getenv('OPENAI_API_BASE')
        self.model = os.getenv('MODEL')
        
    def call_openai_api(self, messages: List[Dict[str, str]], model: str = None, temperature: float = 0.7, max_tokens: int = 500) -> Optional[Dict[str, Any]]:
        if not self.api_key or not self.api_base:
            raise ValueError("API key or base URL not configured")
        
        if model is None:
            model = self.model
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        data = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            print(f"DEBUG: Calling API at {self.api_base}/chat/completions")
            print(f"DEBUG: Model: {self.model}")
            print(f"DEBUG: API key exists: {bool(self.api_key)}")
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result
            else:
                print(f"API request failed, status code: {response.status_code}")
                print(f"Error message: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return None

class IntentUnderstandingAgent(Agent):
    def __init__(self):
        super().__init__("IntentUnderstandingAgent", "Analyze user queries to determine intent, extract parameters, and understand context")
        
    def analyze_intent(self, user_question: str, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        messages = [
            {
                "role": "system", 
                "content": """You are an intent analysis expert for an e-commerce platform. 
                Your task is to analyze user queries (in any language) and determine their intent, extract relevant parameters, 
                and understand the context from conversation history.
                
                Possible intents include:
                - product_recommendation: User wants product suggestions
                - product_details: User asks about specific product details
                - price_inquiry: User wants to know about pricing
                - category_exploration: User wants to explore a product category
                - comparison: User wants to compare products
                - other: Other types of queries
                
                Extract parameters like:
                - categories: Product categories mentioned (e.g., shoes, laptops, phones)
                - features: Specific features requested (e.g., lightweight, waterproof, long battery life)
                - price_range: Price range if mentioned (e.g., {'min': 500, 'max': 1000})
                - product_names: Specific product names mentioned (e.g., Nintendo Switch, PlayStation 5)
                - brands: Brand names mentioned (e.g., Nike, Apple, Samsung, Nintendo, Sony)
                - quantity: Number of products needed
                
                CRITICAL RULES:
                1. ALWAYS extract product categories from user queries and put them in the 'categories' parameter
                2. ALWAYS extract specific features from user queries and put them in the 'features' parameter
                3. For Chinese queries, translate categories and features to English for consistency with product data
                4. Distinguish between brands and product names: Brand names refer to manufacturers (e.g., Nintendo, Sony), while product names refer to specific models (e.g., Nintendo Switch, PlayStation 5)
                5. If a query mentions "a [brand] product" (e.g., "a Nintendo product"), extract [brand] as a brand parameter, not as a product name
                
                Examples:
                - Query: '推荐一些运动鞋' -> categories: ['sports shoes']
                - Query: '推荐一款轻薄的笔记本电脑' -> categories: ['laptop'], features: ['lightweight']
                - Query: '我想要防水的跑步鞋' -> categories: ['running shoes'], features: ['waterproof']
                - Query: 'I need a Pad' -> categories: ['tablet']
                - Query: 'I want a tablet' -> categories: ['tablet']
                
                Also analyze context from conversation history to understand references and preferences.
                
                Return JSON format with:
                {
                    "intent": "intent_name",
                    "parameters": {"key1": "value1", "key2": "value2"},
                    "context": {"reference": "product_id or name if referenced", "preferences": ["preference1", "preference2"]}
                }"""
            }
        ]
        
        if conversation_history:
            for msg in conversation_history:
                messages.append(msg)
        
        messages.append({
            "role": "user", 
            "content": user_question
        })
        
        result = self.call_openai_api(messages)
        
        if result:
            try:
                content = result['choices'][0]['message']['content'].strip()

                if content.startswith('```json'):
                    content = content[7:].strip()
                if content.endswith('```'):
                    content = content[:-3].strip()
                intent_data = json.loads(content)
                return intent_data
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error parsing intent data: {e}")
                print(f"Raw content: {result['choices'][0]['message']['content']}")
        
        return {
            "intent": "product_recommendation",
            "parameters": {},
            "context": {}
        }

class RecommendationAgent(Agent):
    def __init__(self, recommendation_engine: RecommendationEngine):
        super().__init__("RecommendationAgent", "Generate product recommendations based on user intent and preferences")
        self.recommendation_engine = recommendation_engine
        
    def get_recommendations(self, user_question: str, intent_data: Dict[str, Any], 
                          conversation_history: List[Dict[str, str]], last_recommendations: Optional[list]=None) -> List[Dict[str, Any]]:
        if intent_data.get('intent') == 'price_inquiry':
            product_ids = intent_data.get('parameters', {}).get('product_ids') or last_recommendations
            if product_ids:
                matched = [p for p in self.recommendation_engine.products if p.get('id') in product_ids]
                if matched:
                    print(f"DEBUG: Returning price inquiry recommendations: {[p['name'] for p in matched]}")
                    return matched

        raw_recommendations = self.recommendation_engine.recommend_by_text(
            user_question, top_k=10
        )
        print(f"DEBUG: Raw recommendations: {[p['product']['name'] for p in raw_recommendations]}")
        
        product_recommendations = [p['product'] for p in raw_recommendations]
        
        refined_recommendations = self._refine_recommendations(product_recommendations, intent_data, user_question, conversation_history)
        print(f"DEBUG: Refined recommendations: {[p['name'] for p in refined_recommendations]}")
        
        return refined_recommendations
    
    def _refine_recommendations(self, recommendations: List[Dict[str, Any]], 
                               intent_data: Dict[str, Any], user_question: str, conversation_history: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        if recommendations:
            return recommendations

        if 'categories' in intent_data['parameters']:
            categories = intent_data['parameters']['categories']
            if categories and 'brands' not in intent_data['parameters']:
                query = f"{user_question} {', '.join(categories)}"
                raw_recommendations = self.recommendation_engine.recommend_by_text(
                    query, top_k=10
                )
                refined_recommendations = [p['product'] for p in raw_recommendations]
                
                if refined_recommendations:
                    print(f"DEBUG: Refined recommendations after category filtering: {[p['name'] for p in refined_recommendations]}")
                    return refined_recommendations
        
        if intent_data['intent'] == 'product_details':
            if 'product_names' in intent_data['parameters']:
                product_names = intent_data['parameters']['product_names']
                if product_names:
                    refined_query = f"{user_question} for products: {', '.join(product_names)}"
                    
                    raw_recommendations = self.recommendation_engine.recommend_by_text(
                        refined_query, top_k=20
                    )

                    refined_recommendations = [p['product'] for p in raw_recommendations]
                    
                    if refined_recommendations:
                        return refined_recommendations
        
        elif intent_data['intent'] == 'price_inquiry':
            return [p for p in recommendations if 'price' in p and p['price']]
        
        elif intent_data['intent'] == 'comparison':
            return recommendations[:4]
        
        return recommendations[:5]
    
    def format_recommendations(self, recommendations: List[Dict[str, Any]]) -> str:
        if not recommendations:
            return "No relevant products found"
        
        formatted = []
        for i, product in enumerate(recommendations[:10], 1):
            formatted.append(f"{i}. ID: {product['id']}, Name: {product['name']}, "
                          f"Price: {product['price']}, Category: {product['category']}, "
                          f"Description: {product['description']}")
        
        return "\n".join(formatted)

class CoordinationAgent(Agent):
    def __init__(self, intent_agent: IntentUnderstandingAgent, 
                 recommendation_agent: RecommendationAgent):
        super().__init__("CoordinationAgent", "Manage communication between intent and recommendation agents and generate final responses")
        self.intent_agent = intent_agent
        self.recommendation_agent = recommendation_agent
        
    def handle_user_query(self, user_question: str, 
                         conversation_history: List[Dict[str, str]],
                         user_id: Optional[str] = None,
                         last_recommendations: Optional[list] = None) -> Dict[str, Any]:
        intent_data = self.intent_agent.analyze_intent(user_question, conversation_history)
        print(f"DEBUG: Intent data: {intent_data}")

        if intent_data.get('intent') == 'price_inquiry':
            params = intent_data.setdefault('parameters', {})
            if not params.get('product_names') and not params.get('product_ids') and last_recommendations:
                params['product_ids'] = last_recommendations
        
        recommendation_intents = ['product_recommendation', 'category_exploration', 'comparison', 'price_inquiry']
        if intent_data.get('intent') in recommendation_intents:
            recommendations = self.recommendation_agent.get_recommendations(user_question, intent_data, conversation_history, last_recommendations)
        else:
            recommendations = []
        
        response_data = self._generate_response(user_question, intent_data, recommendations, conversation_history)
        reply = response_data.get('reply', 'Sorry, I couldn\'t process your request.')
        
        filtered_products = []
        if recommendations and intent_data.get('intent') in recommendation_intents:
            reply_lower = reply.lower()
            for product in recommendations:
                product_name = product.get('name', '').lower()
                if product_name in reply_lower:
                    filtered_products.append(product)
            
            print(f"DEBUG: Reply: {reply}")
            print(f"DEBUG: Original recommendations: {[p['name'] for p in recommendations]}")
            print(f"DEBUG: Filtered products: {[p['name'] for p in filtered_products]}")
        
        return {
            'reply': reply,
            'products': filtered_products if intent_data.get('intent') in recommendation_intents else [],
            'intent': intent_data['intent'],
            'parameters': intent_data['parameters']
        }
    
    def _generate_response(self, user_question: str, intent_data: Dict[str, Any],
                          recommendations: List[Dict[str, Any]],
                          conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        formatted_recommendations = self.recommendation_agent.format_recommendations(recommendations)
        
        messages = [
            {
                "role": "system", 
                "content": """You are a professional assistant for an e-commerce platform. 
                The products provided in the recommendations list are sourced exclusively from our products.json database.
                Your task is to provide helpful and friendly responses based on user intent, these provided recommendations, and conversation history.
                
                ==== ABSOLUTE, NON-NEGOTIABLE RULES (MUST NOT BE VIOLATED) ====
                1. YOU MUST ONLY RECOMMEND OR MENTION PRODUCTS THAT ARE EXPLICITLY INCLUDED IN THE PROVIDED RECOMMENDED PRODUCTS LIST. THESE ARE THE ONLY PRODUCTS AVAILABLE IN OUR DATABASE (products.json).
                2. YOU MUST NEVER INVENT, HALLUCINATE, OR MENTION ANY PRODUCTS THAT ARE NOT IN THE PROVIDED RECOMMENDATIONS LIST.
                3. YOU MUST NEVER REFER TO PRODUCTS NOT EXPLICITLY PROVIDED IN THE RECOMMENDATIONS, EVEN IF THEY SEEM RELEVANT.
                4. IF NO RECOMMENDED PRODUCTS ARE PROVIDED OR THE LIST IS EMPTY, YOU MUST NOT MENTION ANY PRODUCTS AT ALL.
                5. YOU MUST ONLY USE THE EXACT PRODUCT NAMES, PRICES, CATEGORIES, AND DESCRIPTIONS PROVIDED IN THE RECOMMENDED PRODUCTS LIST.
                6. YOU MUST NOT CREATE, ADD, OR IMPLY ANY PRODUCTS THAT ARE NOT EXPLICITLY PROVIDED IN THE RECOMMENDED PRODUCTS LIST.
                7. IF THE USER ASKS FOR PRODUCTS NOT AVAILABLE IN OUR DATABASE (e.g., groceries, food items), POLITELY EXPLAIN THAT WE DON'T CARRY THOSE PRODUCTS.
                ==== END ABSOLUTE RULES ====
                
                Guidelines:
                1. For product_recommendation intent: Present ALL recommendations clearly with key details (name, price, category, description) EXACTLY as provided. YOU MUST INCLUDE EVERY PRODUCT FROM THE RECOMMENDED PRODUCTS LIST IN YOUR REPLY.
                2. For product_details intent: Focus exclusively on specific product information ONLY from the provided recommendations list.
                3. For price_inquiry: Emphasize pricing information ONLY from the provided recommendations list.
                4. For category_exploration: Provide an overview of the category using examples EXCLUSIVELY from the provided recommendations list.
                5. For comparison: Highlight key differences between products EXCLUSIVELY from the provided recommendations list.
                6. For other intents: ONLY provide the requested information. DO NOT mention anything about products, shopping, or recommendations at all.
                7. If the user asks for products not in our database (like groceries/food when we only sell electronics, games, shoes, home decor, etc.), politely explain that we don't carry those products.
                """
            }
        ]
        
        if conversation_history:
            for msg in conversation_history:
                messages.append(msg)
        
        intent_info = f"User intent: {intent_data['intent']}\nIntent parameters: {intent_data['parameters']}\n"
        
        recommendation_intents = ['product_recommendation', 'category_exploration', 'comparison', 'price_inquiry']
        if recommendations and intent_data.get('intent') in recommendation_intents:
            intent_info += f"Recommended products:\n{formatted_recommendations}"
        elif intent_data.get('intent') in recommendation_intents:
            intent_info += "NO RECOMMENDED PRODUCTS FOUND. YOU MUST NOT MENTION ANY PRODUCTS AT ALL."
        elif intent_data.get('intent') == 'other':
            intent_info += "THIS IS A NON-PRODUCT QUERY. ONLY PROVIDE THE REQUESTED INFORMATION. DO NOT MENTION ANY PRODUCTS, SHOPPING, OR RECOMMENDATIONS."
        
        messages.append({
            "role": "system", 
            "content": intent_info
        })
        
        messages.append({
            "role": "user", 
            "content": user_question
        })
        
        result = self.call_openai_api(messages)
        
        if result:
            try:
                content = result['choices'][0]['message']['content'].strip()
                
                return {
                    'reply': content
                }
            except KeyError as e:
                print(f"Error accessing response content: {e}")
                print(f"Raw result: {result}")
        
        return {
            'reply': "Sorry, I couldn't generate a proper response. Please try again",
        }

intent_agent = IntentUnderstandingAgent()
recommendation_engine = get_recommendation_engine()
recommendation_agent = RecommendationAgent(recommendation_engine)
coordination_agent = CoordinationAgent(intent_agent, recommendation_agent)

def process_query(user_question: str, conversation_history: Optional[List[Dict[str, str]]] = None, 
                 user_id: Optional[str] = None, last_recommendations: Optional[list]=None) -> Dict[str, Any]:
    try:
        if conversation_history is None:
            conversation_history = []
            
        result = coordination_agent.handle_user_query(user_question, conversation_history, user_id, last_recommendations)
        
        return {
            'reply': result['reply'],
            'products': result.get('products', [])
        }
        
    except Exception as e:
        print(f"Error processing query with multi-agent system: {e}")
        import traceback
        traceback.print_exc()
        return {
            'reply': "Sorry, an error occurred while processing your request. Please try again later."
        }