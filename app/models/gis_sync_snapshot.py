"""Snapshot GIS por conta Firebase e coleção, com controle otimista de versão."""
from datetime import datetime, timezone
from app import db


class GisSyncSnapshot(db.Model):
    __tablename__ = 'gis_sync_snapshots'
    __table_args__ = (
        db.UniqueConstraint('firebase_uid', 'collection', name='uq_gis_sync_uid_collection'),
    )

    id = db.Column(db.Integer, primary_key=True)
    firebase_uid = db.Column(db.String(128), nullable=False, index=True)
    collection = db.Column(db.String(32), nullable=False)
    version = db.Column(db.Integer, nullable=False, default=1)
    payload = db.Column(db.JSON, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
