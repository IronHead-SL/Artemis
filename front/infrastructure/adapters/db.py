from __future__ import annotations

import os

import open_clip
import streamlit as st
from pymongo import MongoClient
from qdrant_client import QdrantClient
from neo4j import GraphDatabase


@st.cache_resource(show_spinner=False)
def get_clip_model():
    model, _, preprocess = open_clip.create_model_and_transforms(
        "ViT-B-32", pretrained="laion2b_s34b_b79k"
    )
    model.eval()
    return model, preprocess


@st.cache_resource(show_spinner=False)
def get_mongo_db():
    uri = os.getenv("MONGO_URI", "mongodb://admin:password@mongodb:27017/")
    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    return client[os.getenv("MONGO_DB", "artemis_db")]


@st.cache_resource(show_spinner=False)
def get_qdrant() -> QdrantClient:
    return QdrantClient(
        host=os.getenv("QDRANT_HOST", "qdrant"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
    )


@st.cache_resource(show_spinner=False)
def get_neo4j():
    return GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://neo4j:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password")),
        max_connection_pool_size=10,
    )
