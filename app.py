from flask import Flask, jsonify, request
import pandas as pd
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

# Directory for uploaded files
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variables to hold data
grades_data = []
study_topics_data = {}

# Load study topics from Excel at startup
def load_study_topics():
    global study_topics_data
    try:
        df = pd.read_excel('study_topics.xlsx')
        if 'Course' in df.columns and 'Topic' in df.columns:
            study_topics_data = df.groupby('Course')['Topic'].apply(list).to_dict()
        else:
            print("⚠️ 'Course' or 'Topic' column missing in study_topics.xlsx")
    except Exception as e:
        print(f"Error loading study topics: {e}")

load_study_topics()

# GPA Mapping Function
def calculate_gpa(score):
    if score >= 90:
        return 4.0
    elif score >= 85:
        return 3.67
    elif score >= 80:
        return 3.33
    elif score >= 75:
        return 3.0
    elif score >= 70:
        return 2.67
    elif score >= 65:
        return 2.33
    elif score >= 60:
        return 2.0
    else:
        return 0.0

# File Upload Endpoint
@app.route('/api/upload', methods=['POST'])
def upload_file():
    global grades_data
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.endswith('.xlsx'):
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        grades_data = process_file(filepath)
        if not grades_data:
            return jsonify({"error": "Invalid file structure or empty file."}), 400
        return jsonify({"message": "File uploaded and processed successfully."}), 200

    return jsonify({"error": "Invalid file format"}), 400

# Process uploaded Excel file
def process_file(filepath):
    df = pd.read_excel(filepath)

    required_columns = ['Student Name', 'Course', 'Quiz 1', 'Quiz 2', 'Quiz 3',
                        'Assignment 1', 'Assignment 2', 'Assignment 3', 'Target Grade', 'Course Weight']

    if not all(col in df.columns for col in required_columns):
        print("⚠️ Missing required columns.")
        return []

    processed_data = []
    for _, row in df.iterrows():
        # Handle missing or invalid data
        try:
            quiz_scores = [max(0, min(row[f'Quiz {i}'], 5)) for i in range(1, 4)]  # Each quiz out of 5
            assignment_scores = [max(0, min(row[f'Assignment {i}'], 5)) for i in range(1, 4)]  # Each assignment out of 5

            total_obtained = sum(quiz_scores) + sum(assignment_scores)
            total_possible = 30  # 3 quizzes + 3 assignments, each out of 5

            percentage = (total_obtained / total_possible) * 100
            percentage = min(percentage, 100)  # Cap at 100%

            gpa = calculate_gpa(percentage)

            processed_data.append({
                'Student Name': row['Student Name'],
                'Course': row['Course'],
                'Current Grade': round(percentage, 2),
                'GPA': gpa,
                'Target Grade': row['Target Grade'],
                'Course Weight': row['Course Weight']
            })
        except Exception as e:
            print(f"Error processing row: {e}")

    return processed_data

# Get Grades Endpoint
@app.route('/api/grades', methods=['GET'])
def get_grades():
    return jsonify(grades_data)

# Course of Action Endpoint
@app.route('/api/course_of_action', methods=['GET'])
def get_course_of_action():
    course_of_action = []
    for row in grades_data:
        try:
            # Safely convert to float and strip spaces
            current_grade = float(str(row['Current Grade']).strip())
            target_grade = float(str(row['Target Grade']).strip())
            course_weight = float(str(row['Course Weight']).strip())

            # Calculate deficit with precision handling
            deficit = round(target_grade - current_grade, 2)

            if deficit > 0:
                # Calculate study hours based on deficit and course weight
                import math
                hours_needed = round(math.sqrt(deficit * row['Course Weight']) * 2, 1)

                topics = study_topics_data.get(row['Course'], ['General Review'])
                action = f"📘 Study '{row['Course']}' for {hours_needed} hours. Focus on: {', '.join(topics)}."
                course_of_action.append(action)
            else:
                action = f"✅ You have met the target for '{row['Course']}'. Great job!"
                course_of_action.append(action)

        except Exception as e:
            print(f"Error generating course of action for {row.get('Course', 'Unknown')}: {e}")
            course_of_action.append(f"⚠️ Error processing course '{row.get('Course', 'Unknown')}'.")

    if not course_of_action:
        course_of_action.append("🎉 All targets are met. No additional study required.")

    return jsonify(course_of_action)


# Performance Indicators Endpoint
@app.route('/api/performance_indicators', methods=['GET'])
def get_performance_indicators():
    if not grades_data:
        return jsonify({"error": "No data available"}), 400

    df = pd.DataFrame(grades_data)
    performance_indicators = {
        'average_current_grade': round(df['Current Grade'].mean(), 2),
        'average_gpa': round(df['GPA'].mean(), 2),
        'average_target_grade': round(df['Target Grade'].mean(), 2),
        'average_course_weight': round(df['Course Weight'].mean(), 2)
    }
    return jsonify(performance_indicators)

if __name__ == '__main__':
    app.run(debug=True)
