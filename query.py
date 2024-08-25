from flask import Flask, jsonify, request, send_file
import sqlite3
import uuid
import threading
import pandas as pd
from datetime import datetime, timedelta

conn = sqlite3.connect('store_monitoring.db')
c = conn.cursor()
c.execute("SELECT DISTINCT store_id FROM menu_hours")
store_ids = [row[0] for row in c.fetchall()]
conn.close()