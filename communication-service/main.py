from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# -------------------------
# MODELE
# -------------------------

class Message(BaseModel):
    id: int
    author: str
    content: str

class ForumPost(BaseModel):
    id: int
    title: str
    content: str
    author: str

class Comment(BaseModel):
    id: int
    post_id: int
    author: str
    content: str

# -------------------------
# DANE W PAMIĘCI
# -------------------------

messages: List[Message] = []
forum_posts: List[ForumPost] = []
comments: List[Comment] = []

# -------------------------
# ENDPOINTY CZATU
# -------------------------

@app.get("/chat", response_model=List[Message])
def get_messages():
    return messages

@app.post("/chat", response_model=Message)
def send_message(msg: Message):
    messages.append(msg)
    return msg

# -------------------------
# ENDPOINTY FORUM
# -------------------------

@app.get("/forum", response_model=List[ForumPost])
def get_forum_posts():
    return forum_posts

@app.post("/forum", response_model=ForumPost)
def add_forum_post(post: ForumPost):
    forum_posts.append(post)
    return post

# -------------------------
# KOMENTARZE
# -------------------------

@app.get("/comments/{post_id}", response_model=List[Comment])
def get_comments(post_id: int):
    return [c for c in comments if c.post_id == post_id]

@app.post("/comments", response_model=Comment)
def add_comment(comment: Comment):
    comments.append(comment)
    return comment
