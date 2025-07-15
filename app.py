from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import tempfile
import os
from medical_extractor import MedicalExtractor

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize the extractor
extractor = MedicalExtractor()

@app.route('/')
def index():
    """Serve the main dashboard"""
    with open('index.html', 'r') as f:
        return render_template_string(f.read())

@app.route('/api/analyze', methods=['POST'])
def analyze_pdf():
    """Analyze uploaded PDF using the medical extractor"""
    try:
        # Check if PDF file was uploaded
        if 'pdf' not in request.files:
            return jsonify({'error': 'No PDF file uploaded'}), 400
        
        pdf_file = request.files['pdf']
        
        if pdf_file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not pdf_file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'File must be a PDF'}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            pdf_file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Process PDF using your extractor
            results = extractor.process_pdf(temp_path)
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            # Return results as JSON
            return jsonify({
                'success': True,
                'data': results
            })
            
        except Exception as processing_error:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            
            return jsonify({
                'error': f'Error processing PDF: {str(processing_error)}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'message': 'Medical PDF Analysis API is running'
    })

@app.route('/api/clinical-ranges', methods=['GET'])
def get_clinical_ranges():
    """Get clinical reference ranges"""
    return jsonify({
        'clinical_ranges': extractor.clinical_ranges
    })

if __name__ == '__main__':
    # For development
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)