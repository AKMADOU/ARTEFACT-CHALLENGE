#!/usr/bin/env python3
"""
search.py — TF-IDF RAG search for customer reviews
Semantic search on review text using bigrammes + unigrams
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class ReviewIndex:
    """
    TF-IDF search index for customer reviews.
    Supports filtering by route, sentiment, and ranking by relevance.
    """
    
    def __init__(self, reviews_df: pd.DataFrame):
        """
        Initialize index from reviews dataframe.
        
        Args:
            reviews_df: DataFrame with columns:
                - review_id, route_id, review_text, sentiment_bucket, topics
        """
        self.reviews_df = reviews_df.copy()
        
        # Build TF-IDF vectorizer (unigrams + bigrams)
        self.vectorizer = TfidfVectorizer(
            analyzer="char",
            ngram_range=(2, 3),  # bigrammes + trigrammes de caractères
            max_features=3000,
            lowercase=True,
            stop_words="english",
        )
        
        try:
            # Fit on review texts
            self.tfidf_matrix = self.vectorizer.fit_transform(
                self.reviews_df["review_text"].fillna("")
            )
        except Exception as e:
            raise ValueError(f"Failed to build TF-IDF index: {e}")
    
    def search(
        self,
        query: str,
        route_id: str = None,
        sentiment: str = None,
        top_k: int = 8,
    ) -> pd.DataFrame:
        """
        Search reviews by TF-IDF similarity.
        
        Args:
            query: Search keywords (e.g., "delay communication", "food quality")
            route_id: Optional route filter
            sentiment: Optional sentiment filter ("Promoter", "Passive", "Detractor")
            top_k: Number of results
        
        Returns:
            DataFrame with top_k matching reviews + similarity_score
        """
        query = query.strip()
        if not query:
            return pd.DataFrame()
        
        # Transform query
        query_vector = self.vectorizer.transform([query])
        
        # Compute similarities
        similarities = cosine_similarity(query_vector, self.tfidf_matrix)[0]
        
        # Add to dataframe
        results = self.reviews_df.copy()
        results["similarity_score"] = similarities
        
        # Filter by route
        if route_id:
            results = results[results["route_id"] == route_id.strip()]
        
        # Filter by sentiment
        if sentiment:
            results = results[results["sentiment_bucket"] == sentiment.strip()]
        
        # Sort by similarity, take top_k
        results = results.sort_values("similarity_score", ascending=False).head(top_k)
        
        return results if not results.empty else pd.DataFrame()


def get_index(reviews_df: pd.DataFrame) -> ReviewIndex:
    """
    Create a TF-IDF search index from reviews.
    
    Args:
        reviews_df: DataFrame with review texts and metadata
    
    Returns:
        ReviewIndex instance ready for searching
    """
    return ReviewIndex(reviews_df)
