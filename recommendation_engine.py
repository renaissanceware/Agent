import json
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

class RecommendationEngine:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.products = self._load_products()
        self.product_texts = self._prepare_product_texts()
        self.vectors = self.model.encode(self.product_texts)
        self.index = self._create_faiss_index(self.vectors)
    
    def _load_products(self):
        product_path = os.path.join(os.path.dirname(__file__), 'data', 'products.json')
        with open(product_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _prepare_product_texts(self):
        texts = []
        for product in self.products:
            text = f"{product['name']} {product['description']} {product['brand']} {product['category']}"
            texts.append(text)
        return texts
    
    def _create_faiss_index(self, vectors):
        dimension = vectors.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(np.array(vectors).astype('float32'))
        return index
    
    def recommend_products(self, product_id, top_k=5):
        product_index = None
        for i, product in enumerate(self.products):
            if product['id'] == product_id:
                product_index = i
                break
        
        if product_index is None:
            raise ValueError(f"Didn't find product with id {product_id}.")
        
        query_vector = np.array([self.vectors[product_index]]).astype('float32')
        
        distances, indices = self.index.search(query_vector, top_k + 1)
        
        recommended_products = []
        for i in range(1, top_k + 1):
            idx = indices[0][i]
            recommended_products.append({
                'product': self.products[idx],
                'similarity': 1 / (1 + distances[0][i])
            })
        
        return recommended_products
    
    def recommend_by_text(self, text, top_k=5):
        query_vector = self.model.encode([text])
        query_vector = np.array(query_vector).astype('float32')

        distances, indices = self.index.search(query_vector, top_k)
        
        recommended_products = []
        for i in range(top_k):
            idx = indices[0][i]
            recommended_products.append({
                'product': self.products[idx],
                'similarity': 1 / (1 + distances[0][i])
            })
        
        return recommended_products
    
    def get_product_by_id(self, product_id):
        for product in self.products:
            if product['id'] == product_id:
                return product
        return None

engine = None

def get_recommendation_engine():
    global engine
    if engine is None:
        engine = RecommendationEngine()
    return engine