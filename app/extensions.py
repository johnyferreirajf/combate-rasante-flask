"""
extensions.py
Instâncias das extensões Flask, inicializadas sem app (Application Factory pattern).
Importadas em app/__init__.py via init_app().
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
