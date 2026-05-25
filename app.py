import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import cv2
import pytesseract
from passporteye import read_mrz

# Point pytesseract to the newly installed Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

app = Flask(__name__)
# Enables safe cross-origin communication between your HTML file and the Python backend
CORS(app)

def process_passport_image(image_path):
    try:
        # Load image via OpenCV
        img = cv2.imread(image_path)
        if img is None:
            return {"error": "Invalid image file. The system could not read the file format."}
            
        # Convert image to grayscale to make the MRZ text punchy and high-contrast
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        temp_processed_path = "temp_processing.jpg"
        cv2.imwrite(temp_processed_path, gray)

        # Scan and read the raw MRZ lines from the processed image using passporteye
        mrz = read_mrz(temp_processed_path)
        
        # Clean up temporary processing image immediately
        if os.path.exists(temp_processed_path):
            os.remove(temp_processed_path)

        if mrz is None:
            return {
                "error": "Could not read the Machine Readable Zone (MRZ). Please ensure the passport text at the bottom is flat, clear, and free from bright light glares."
            }

        mrz_data = mrz.to_dict()

        # Clean filler brackets (<) out of text strings cleanly
        clean_given_names = mrz_data.get('names', '').replace('<', ' ').strip().title()
        clean_surname = mrz_data.get('surname', '').replace('<', ' ').strip().title()
        clean_passport_number = mrz_data.get('number', '').replace('<', '').strip()

        # Simple function to format raw YYMMDD strings to readable YYYY-MM-DD format safely
        def format_mrz_date(raw_date, century_prefix="20"):
            if not raw_date or len(raw_date) < 6:
                return ""
            year = raw_date[0:2]
            month = raw_date[2:4]
            day = raw_date[4:6]
            # Handle split century assumptions safely for birthdates
            if century_prefix == "19/20":
                prefix = "19" if int(year) > 30 else "20"
            else:
                prefix = century_prefix
            return f"{prefix}{year}-{month}-{day}"

        return {
            "success": True,
            "passport_number": clean_passport_number,
            "surname": clean_surname,
            "given_names": clean_given_names,
            "nationality": mrz_data.get('nationality', ''),
            "dob": format_mrz_date(mrz_data.get('date_of_birth', ''), "19/20"),
            "gender": "Male" if mrz_data.get('sex') == "M" else "Female" if mrz_data.get('sex') == "F" else mrz_data.get('sex', ''),
            "expiry_date": format_mrz_date(mrz_data.get('expiration_date', ''), "20")
        }
        
    except Exception as e:
        return {"error": f"Internal extraction error: {str(e)}"}

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/scan', methods=['POST'])
def scan_endpoint():
    if 'passport_image' not in request.files:
        return jsonify({"error": "No passport image file detected in request payload."}), 400
        
    uploaded_file = request.files['passport_image']
    temporary_save_path = "active_upload.jpg"
    
    try:
        uploaded_file.save(temporary_save_path)
        scan_results = process_passport_image(temporary_save_path)
        return jsonify(scan_results)
    finally:
        # Guarantee removal of uploaded source asset file for user privacy
        if os.path.exists(temporary_save_path):
            os.remove(temporary_save_path)

if __name__ == '__main__':
    print("--------------------------------------------------")
    print("  Sri Lankan Passport Free OCR Engine Online Ready")
    print("--------------------------------------------------")
    app.run(host='0.0.0.0', port=5000, debug=True)