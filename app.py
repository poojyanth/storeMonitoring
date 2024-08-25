from flask import Flask, jsonify, request, send_file
import sqlite3
import uuid
import threading
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('store_monitoring.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS menu_hours
                 (store_id TEXT, day INTEGER, start_time_local TEXT, end_time_local TEXT)''')
    conn.commit()
    conn.close()

init_db()

# This dictionary will store the status of each report
reports = {}

def load_csv_to_db(file_path):
    conn = sqlite3.connect('store_monitoring.db')
    df = pd.read_csv(file_path)
    df.to_sql('menu_hours', conn, if_exists='replace', index=False)
    conn.close()

# Load CSV data into the database (you should call this function with the correct file path)
load_csv_to_db('./data/Menu hours.csv')

def get_business_hours(store_id):
    conn = sqlite3.connect('store_monitoring.db')
    c = conn.cursor()
    c.execute("SELECT day, start_time_local, end_time_local FROM menu_hours WHERE store_id = ?", (store_id,))
    results = c.fetchall()
    conn.close()
    if not results:
        return {i: ('00:00:00', '23:59:59') for i in range(7)}
    return {row[0]: (row[1], row[2]) for row in results}

def calculate_uptime_downtime(store_id, start_time, end_time):
    business_hours = get_business_hours(store_id)
    
    current_time = start_time
    uptime = timedelta()
    downtime = timedelta()
    
    while current_time <= end_time:
        current_day = current_time.weekday()
        current_time_str = current_time.strftime('%H:%M:%S')
        
        if current_day in business_hours:
            start_time_local, end_time_local = business_hours[current_day]
            if start_time_local <= current_time_str <= end_time_local:
                uptime += timedelta(hours=1)
            else:
                downtime += timedelta(hours=1)
        else:
            downtime += timedelta(hours=1)
        
        current_time += timedelta(hours=1)
    
    return uptime, downtime

def generate_report(report_id):
    print(f"Generating report {report_id}...")
    conn = sqlite3.connect('store_monitoring.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT store_id FROM menu_hours")
    store_ids = [row[0] for row in c.fetchall()]
    conn.close()

    end_time = datetime.utcnow()
    start_time_week = end_time - timedelta(days=7)
    start_time_day = end_time - timedelta(days=1)
    start_time_hour = end_time - timedelta(hours=1)

    report_data = []
    for store_id in store_ids:
        uptime_week, downtime_week = calculate_uptime_downtime(store_id, start_time_week, end_time)
        uptime_day, downtime_day = calculate_uptime_downtime(store_id, start_time_day, end_time)
        uptime_hour, downtime_hour = calculate_uptime_downtime(store_id, start_time_hour, end_time)

        report_data.append({
            'store_id': store_id,
            'uptime_last_hour': round(uptime_hour.total_seconds() / 60, 2),
            'uptime_last_day': round(uptime_day.total_seconds() / 3600, 2),
            'uptime_last_week': round(uptime_week.total_seconds() / 3600, 2),
            'downtime_last_hour': round(downtime_hour.total_seconds() / 60, 2),
            'downtime_last_day': round(downtime_day.total_seconds() / 3600, 2),
            'downtime_last_week': round(downtime_week.total_seconds() / 3600, 2)
        })

    reports[report_id] = report_data
    print(f"Report {report_id} generated.")

@app.route('/', methods=['GET'])
def index():
    homepage = """
    <h1>Store Monitoring System</h1>
    <p>Welcome to the Store Monitoring System. You can trigger a report by sending a GET request to <a href="/trigger_report">/trigger_report</a>.
    You can then check the status of the report by sending a GET request to <a href="/get_report?report_id=< report_id >">/get_report?report_id=< report_id ></a>.
    Once the report is generated, you can download the report</p>
    """
    return homepage
    


@app.route('/trigger_report', methods=['GET'])
def trigger_report():
    report_id = str(uuid.uuid4())
    reports[report_id] = "Running"
    
    thread = threading.Thread(target=generate_report, args=(report_id,))
    thread.start()
    
    return jsonify({"report_id": report_id})

@app.route('/get_report', methods=['GET'])
def get_report():
    report_id = request.args.get('report_id')
    if report_id not in reports:
        return jsonify({"error": "Report not found"}), 404
    
    if reports[report_id] == "Running":
        return jsonify({"status": "Running"})
    
    # convert reports[report_id] to csv file and return the file
    report_df = pd.DataFrame(reports[report_id])
    report_df.to_csv(f'report_{report_id}.csv', index=False)
    
    # send the file to the user
    return send_file(f'report_{report_id}.csv', as_attachment=True)
    

if __name__ == '__main__':
    app.run(debug=True)