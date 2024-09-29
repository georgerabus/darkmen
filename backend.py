from flask import Flask, request, jsonify, send_file, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')  # Serve the HTML file

@app.route('/api/generate', methods=['POST'])
def generate():
    filename = 'triangles.png'
    # Logic to create the image goes here (if needed)
    return jsonify({"image_url": f"/images/{filename}"})

@app.route('/images/<filename>', methods=['GET'])
def serve_image(filename):
    return send_file(filename, mimetype='image/png')

@app.route('/api/files', methods=['GET'])
def get_files():
    # Assuming you have a directory with files
    files = os.listdir('data')
    # Return files as a JSON response
    return jsonify(files)


if __name__ == '__main__':
    app.run(debug=True)
