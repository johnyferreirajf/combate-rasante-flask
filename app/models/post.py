from datetime import datetime
from app import db


class Post(db.Model):
    __tablename__ = "posts"

    id         = db.Column(db.Integer,     primary_key=True)
    titulo     = db.Column(db.String(200), nullable=False)
    descricao  = db.Column(db.Text,        nullable=True)
    created_at = db.Column(db.DateTime,    default=datetime.utcnow)
    ativo      = db.Column(db.Boolean,     default=True)

    midias = db.relationship("PostMidia", backref="post",
                             cascade="all, delete-orphan",
                             order_by="PostMidia.ordem")

    def __repr__(self):
        return f"<Post {self.id} {self.titulo}>"


class PostMidia(db.Model):
    __tablename__ = "post_midias"

    id        = db.Column(db.Integer,      primary_key=True)
    post_id   = db.Column(db.Integer,      db.ForeignKey("posts.id"), nullable=False)
    tipo      = db.Column(db.String(20),   nullable=False)    # "foto" | "video"
    url       = db.Column(db.Text,         nullable=False)    # URL Cloudinary ou YouTube
    public_id = db.Column(db.String(255),  nullable=True)     # Cloudinary public_id
    ordem     = db.Column(db.Integer,      default=0)

    def __repr__(self):
        return f"<PostMidia {self.tipo} post={self.post_id}>"
