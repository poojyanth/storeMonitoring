# models.py
from db_setup import db

class StoreHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.String, nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)
    start_time_local = db.Column(db.Time, nullable=False)
    end_time_local = db.Column(db.Time, nullable=False)
