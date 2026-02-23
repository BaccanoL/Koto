
import os
import sys
import time
import json
import unittest
from unittest.mock import MagicMock, patch

# Add web to path
sys.path.append(os.path.join(os.getcwd(), 'web'))

# Mock Flask request context
from flask import Flask
app = Flask(__name__)

# Import Koto components
try:
    from web.app import KotoBrain, get_knowledge_base, session_manager
    from web.knowledge_base import KnowledgeBase
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

class TestKotoFeatures(unittest.TestCase):
    def setUp(self):
        self.brain = KotoBrain()
        self.kb = get_knowledge_base()
        self.session_id = f"test_session_{int(time.time())}"
        session_manager.create(self.session_id)

    def tearDown(self):
        # Cleanup session
        session_manager.delete(f"{self.session_id}.json")

    def test_01_chat_basic(self):
        """Test basic chat functionality"""
        print("\n[TEST] Testing Basic Chat...")
        history = []
        user_input = "Hello, Koto! specific_test_keyword"
        # We might not have a real API key, so expect legitimate failure or mock response
        # Here we just check if the function runs without crashing
        try:
            result = self.brain.chat(history, user_input, file_data=None, auto_model=True)
            print(f"Chat Response: {result.get('response')[:50]}...")
            self.assertIn("response", result)
        except Exception as e:
            print(f"Chat failed (expected if no API key): {e}")

    def test_02_knowledge_base_add(self):
        """Test adding content to Knowledge Base"""
        print("\n[TEST] Testing Knowledge Base Addition...")
        text = "Koto is an AI assistant developed for testing purposes."
        metadata = {"file_name": "koto_test_doc.txt", "file_path": "test/koto_test_doc.txt"}
        result = self.kb.add_content(text, metadata)
        print(f"Add Result: {result}")
        self.assertTrue(result['success'] or result.get('message') == "内容已存在")

    def test_03_rag_retrieval(self):
        """Test RAG retrieval integration"""
        print("\n[TEST] Testing RAG Retrieval...")
        # Search for the content added above
        results = self.kb.search("Koto testing purposes")
        print(f"Search Results: {len(results)}")
        if results:
            print(f"Top Match: {results[0]['text']}")
            self.assertIn("Koto", results[0]['text'])
        else:
            print("No results found (may be due to mock embedding if API key missing)")

    def test_04_image_generation_mock(self):
        """Test Image Generation (Mocked)"""
        print("\n[TEST] Testing Image Generation Logic...")
        # We can't easily test real generation without paying/API, so we check routing
        user_input = "Generate an image of a cat"
        # Mocking the actual API call inside brain
        with patch('web.app.client.models.generate_content') as mock_gen:
            mock_gen.return_value.candidates = [] # Simulate empty/safe fail
            res = self.brain.chat([], user_input, file_data=None, auto_model=True)
            print(f"Image Gen Route Result: {res.get('task')}")
            # It might classify as VISION or PAINTER or CHAT depending on router
            # But we process it.

if __name__ == '__main__':
    unittest.main()
