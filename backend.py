from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import json
from openai import OpenAI
import threading

app = Flask(__name__)

# Initialize the OpenAI client
client = OpenAI()

@app.route('/')
def index():
    return render_template('index.html')  # Serve the HTML file

@app.route('/api/files', methods=['GET'])
def get_files():
    files = os.listdir('data')
    return jsonify(files)

def chunk_data(data, chunk_size=20000):
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

def chunk_messages(content, max_length=4000):
    chunks = []
    current_chunk = ""

    for message in content.split(" "):
        if len(current_chunk) + len(message) + 1 > max_length:  # +1 for space
            chunks.append(current_chunk)
            current_chunk = message
        else:
            current_chunk += " " + message if current_chunk else message
    
    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def build_prompt(options):
    # Default to basic statistics if no options are selected
    if "Basic Statistics" in options:
        return "Extract useful statistics like number of conversations, lengths, frequency nothing else. Keep it basic"
    elif "Emotional Patterns" in options:
        return "User Sentiment, Satisfaction, Frustration and other emotional patterns Identify from the conversation user sentiment, if the user was happy with the answer, frustrated, or other emotional patterns. ONLY THIS, NOTHING ELSE"
    elif "Trends of Interest" in options:
        return "Extract types of questions, topics, identify trends and other hidden patterns.Identify the most frequently asked questions or discussed topics. ONLY THIS, NOTHING ELSE"
    elif "Hallucination Detection" in options:
        return "Identify instances where a chatbot has hallucinated, i.e., provided responses that are either factually incorrect or not relevant to the question based on its knowledge database. Compare chatbot responses with context_summary. SHOW ONLY ABOUT THIS, NOTHING ELSE"
    else:
        return "Generate a basic summary of the data."

@app.route('/api/read_files', methods=['POST'])
def read_files():
    data = request.get_json()
    selected_files = data.get('files', [])
    selected_options = data.get('options', [])

    combined_content = []

    for filename in selected_files:
        try:
            file_path = os.path.join('data', filename)
            content = read_json_file(file_path)
            if content is not None:
                combined_content.append(content)
            else:
                print(f"Failed to read content from: {filename}")
        except Exception as e:
            print(f"Error processing file {filename}: {str(e)}")

    if combined_content:
        # Combine all content into a string and chunk it
        json_content = json.dumps(combined_content)
        chunks = chunk_data(json_content, chunk_size=20000)

        responses = []
        threads = []

        # Build OpenAI prompt based on selected options
        prompt = build_prompt(selected_options)

        # Process each chunk in a separate thread
        for chunk in chunks:
            thread = threading.Thread(target=lambda c=chunk: responses.append(process_data_with_openai(c, prompt)))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()  # Wait for all threads to finish

        # Aggregate responses
        final_statistics = process_data_with_openai(" ".join(responses), prompt, is_final_call=True)
        
        # Generate and save the report
        report_filename = 'report.json'
        report_path = os.path.join('reports', report_filename)
        os.makedirs('reports', exist_ok=True)

        with open(report_path, 'w') as report_file:
            json.dump({"response": final_statistics}, report_file)

        report_url = f"/api/download_report/{report_filename}"
        return jsonify({"response": final_statistics, "reportUrl": report_url})
    
    return jsonify({"response": "No valid files selected."})

def read_json_file(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            return json.load(file)
    else:
        print(f"File not found: {filepath}")
        return None

def process_data_with_openai(data_content, prompt, is_final_call=False):
    try:
        if is_final_call:
            prompt = "Generate a final summary based on the following responses: "
        
        message_chunks = chunk_messages(data_content)

        responses = []
        for message_chunk in message_chunks:
            completion = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"{prompt} {message_chunk}"}
                ]
            )
            response_message = completion.choices[0].message.content
            responses.append(response_message)

        final_response = " ".join(responses)
        return final_response

    except Exception as e:
        print(f"Error while calling OpenAI API: {e}")
        return None

@app.route('/api/download_report/<filename>', methods=['GET'])
def download_report(filename):
    return send_from_directory('reports', filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
