import pinecone
import tiktoken  # for counting tokens
import openai

from lib.chat_config import ChatConfig

class DBPinecone:
    @classmethod
    def factory(cls, table_name, config: ChatConfig):
        if table_name and config.PINECONE_API_KEY and config.PINECONE_ENVIRONMENT:
            assert table_name in pinecone.list_indexes(), f"No Pinecone table named {table_name}"
            return DBPinecone(table_name, config)
    
    def __init__(self, config: ChatConfig):
        self.config = config
        self.index = pinecone.Index(table_name)
            
    # Fetch artciles related to user messages    
    def _fetch_related_articles(self, messages, model, token_budget: int) -> str:
        """Return related articles with the question using the embedding vector search."""
        query = ""
        for message in messages:
            if message["role"] == "user":
                query = message["content"] + "\n" + query
        query_embedding_response = openai.Embedding.create(
            model=self.config.EMBEDDING_MODEL,
            input=query,
        )
        query_embedding = query_embedding_response["data"][0]["embedding"]

        results = self.index.query(query_embedding, top_k=12, include_metadata=True)

        articles = ""
        count = 0
        base_token = self._messages_tokens(messages, model)
        if self.config.verbose:
            print(f"messages token:{base_token}")
        for match in results["matches"]:
            article = match["metadata"]["text"]
            article_with_section = f'\n\nSection:\n"""\n{article}\n"""'
            if self._num_tokens(articles + article_with_section + query, model) + base_token > token_budget:
                break
            else:
                count += 1
                articles += article_with_section
                if self.config.verbose:
                    print(len(article), self._num_tokens(article, model))
        if self.config.verbose:
            print(f"Articles:{count}, Tokens:{self._num_tokens(articles + query, model)}")
        return articles

    # Returns the number of tokens in a string
    def _num_tokens(self, text: str, model) -> int:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))

    # Returns the total number of tokens in messages    
    def _messages_tokens(self, messages, model) -> int:
        return sum([self._num_tokens(message["content"], model) for message in messages])

