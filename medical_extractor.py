import fitz
import re
import pandas as pd
from typing import Dict

class MedicalExtractor:
    def __init__(self):
        self.clinical_ranges = {
            'Button Press Accuracy': {'normal': 94.1, 'mild_ad': 82.2, 'direction': 'lower'},
            'False Alarms': {'normal': 1.1, 'mild_ad': 4.9, 'direction': 'higher'},
            'Median Reaction Time': {'normal': 458, 'mild_ad': 499, 'direction': 'higher'},
            'P50 Amplitude': {'normal': 2.77, 'mild_ad': 2.95, 'direction': 'higher'},
            'N100 Amplitude': {'normal': -7.23, 'mild_ad': -6.00, 'direction': 'higher'},
            'P200 Amplitude': {'normal': 5.26, 'mild_ad': 4.64, 'direction': 'lower'},
            'N200 Amplitude': {'normal': -0.31, 'mild_ad': -1.10, 'direction': 'lower'},
            'P3b Amplitude': {'normal': 6.03, 'mild_ad': 4.42, 'direction': 'lower'},
            'P3b Latency': {'normal': 396.0, 'mild_ad': 419.6, 'direction': 'higher'},
            'Slow Wave Amplitude': {'normal': -2.54, 'mild_ad': -2.65, 'direction': 'lower'},
            'P3a Amplitude': {'normal': 5.88, 'mild_ad': 3.63, 'direction': 'lower'},
            'Peak Alpha Frequency': {'normal': 9.39, 'mild_ad': 8.34, 'direction': 'lower'}
        }
        
        self.audiogram_frequencies = [250, 500, 1000, 2000, 4000, 8000]
    
    def extract_pdf_text(self, pdf_path: str) -> str:
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            return text
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    
    def calculate_clinical_interpretation(self, metric: str, value: float) -> str:
        if metric not in self.clinical_ranges:
            return 'Unknown'
        
        if metric == 'Peak Alpha Frequency' and value < 8.0:
            return 'CRITICAL - RETEST REQUIRED'
        
        range_info = self.clinical_ranges[metric]
        normal_val = range_info['normal']
        mild_ad_val = range_info['mild_ad']
        direction = range_info['direction']
        
        if direction == 'lower':
            if value <= mild_ad_val:
                return 'High Risk'
            elif value < normal_val:
                return 'Borderline'
            else:
                return 'Normal'
        else:
            if value >= mild_ad_val:
                return 'High Risk'
            elif value > normal_val:
                return 'Borderline'
            else:
                return 'Normal'
    
    def interpret_hearing_loss(self, htl_db: float) -> str:
        if htl_db <= 25:
            return 'Normal'
        elif htl_db <= 40:
            return 'Mild'
        elif htl_db <= 55:
            return 'Moderate'
        else:
            return 'Moderate to Severe'
    
    def analyze_audiogram_asymmetry(self, audiogram_data: Dict) -> Dict:
        asymmetry_analysis = {
            'asymmetries': {},
            'flags': [],
            'max_asymmetry': 0,
            'concerning_frequencies': []
        }
        
        if 'left_ear' not in audiogram_data or 'right_ear' not in audiogram_data:
            return asymmetry_analysis
        
        left_ear = audiogram_data['left_ear']
        right_ear = audiogram_data['right_ear']
        
        for freq in [250, 500, 1000, 2000, 4000, 8000]:
            if freq in left_ear and freq in right_ear:
                asymmetry = abs(left_ear[freq] - right_ear[freq])
                
                if asymmetry <= 25:
                    asymmetry_classification = 'Normal'
                    flag_level = 'NORMAL'
                elif asymmetry <= 40:
                    asymmetry_classification = 'Mild'
                    flag_level = 'MILD_ASYMMETRY'
                elif asymmetry <= 55:
                    asymmetry_classification = 'Moderate'
                    flag_level = 'MODERATE_ASYMMETRY'
                else:
                    asymmetry_classification = 'Moderate to Severe'
                    flag_level = 'SEVERE_ASYMMETRY'
                
                asymmetry_analysis['asymmetries'][freq] = {
                    'left_ear_htl': left_ear[freq],
                    'right_ear_htl': right_ear[freq],
                    'asymmetry_db': asymmetry,
                    'asymmetry_classification': asymmetry_classification,
                    'flag_level': flag_level,
                    'worse_ear': 'left' if left_ear[freq] > right_ear[freq] else 'right'
                }
                
                if asymmetry > asymmetry_analysis['max_asymmetry']:
                    asymmetry_analysis['max_asymmetry'] = asymmetry
                
                if asymmetry > 55:
                    asymmetry_analysis['concerning_frequencies'].append(freq)
                    asymmetry_analysis['flags'].append(
                        f"{freq}Hz: {asymmetry}dB asymmetry (L:{left_ear[freq]}dB, R:{right_ear[freq]}dB) - SEVERE"
                    )
                elif asymmetry > 40:
                    asymmetry_analysis['concerning_frequencies'].append(freq)
                    asymmetry_analysis['flags'].append(
                        f"{freq}Hz: {asymmetry}dB asymmetry (L:{left_ear[freq]}dB, R:{right_ear[freq]}dB) - MODERATE"
                    )
        
        max_asymmetry = asymmetry_analysis['max_asymmetry']
        if max_asymmetry > 55:
            asymmetry_analysis['overall_flag'] = 'SEVERE_ASYMMETRY'
            asymmetry_analysis['clinical_significance'] = 'Moderate to severe asymmetry detected. Immediate audiological referral recommended.'
        elif max_asymmetry > 40:
            asymmetry_analysis['overall_flag'] = 'MODERATE_ASYMMETRY'
            asymmetry_analysis['clinical_significance'] = 'Moderate asymmetry detected. Consider audiological evaluation.'
        elif max_asymmetry > 25:
            asymmetry_analysis['overall_flag'] = 'MILD_ASYMMETRY'
            asymmetry_analysis['clinical_significance'] = 'Mild asymmetry present. Monitor for progression.'
        else:
            asymmetry_analysis['overall_flag'] = 'NORMAL_ASYMMETRY'
            asymmetry_analysis['clinical_significance'] = 'Ear-to-ear differences within normal limits.'
        
        return asymmetry_analysis

    def check_cognision_compatibility(self, audiogram_data: Dict) -> Dict:
        compatibility = {'left_ear': True, 'right_ear': True, 'overall': True}
        issues = []
        
        for ear in ['left_ear', 'right_ear']:
            if ear in audiogram_data:
                for freq, htl in audiogram_data[ear].items():
                    if htl > 45:
                        compatibility[ear] = False
                        compatibility['overall'] = False
                        issues.append(f"{ear.replace('_', ' ').title()}: {freq}Hz = {htl}dB (>45dB limit)")
        
        return {
            'compatible': compatibility['overall'],
            'left_ear_compatible': compatibility['left_ear'],
            'right_ear_compatible': compatibility['right_ear'],
            'issues': issues
        }
    
    def extract_audiogram_data(self, text: str) -> Dict:
        audiogram_data = {}
        lines = [line.strip() for line in text.split('\n')]
        
        for i, line in enumerate(lines):
            if any(pattern in line.lower() for pattern in ['audiogram', 'hearing threshold']):
                pass
        
        return audiogram_data
    
    def generate_study_findings(self, values: Dict, interpretations: Dict, audiogram_data: Dict = None) -> str:
        high_risk_findings = []
        borderline_findings = []
        
        for metric, interpretation in interpretations.items():
            if interpretation == 'High Risk':
                high_risk_findings.append(metric.lower())
            elif interpretation == 'Borderline':
                borderline_findings.append(metric.lower())
        
        if not high_risk_findings and not borderline_findings:
            findings = "This is a normal study with all measured parameters within expected ranges."
        else:
            findings_parts = []
            
            if high_risk_findings:
                if len(high_risk_findings) == 1:
                    findings_parts.append(f"high risk {high_risk_findings[0]}")
                else:
                    findings_parts.append(f"high risk {', '.join(high_risk_findings[:-1])}, and {high_risk_findings[-1]}")
            
            if borderline_findings:
                if len(borderline_findings) == 1:
                    findings_parts.append(f"borderline {borderline_findings[0]}")
                else:
                    findings_parts.append(f"borderline {', '.join(borderline_findings[:-1])}, and {borderline_findings[-1]}")
            
            if len(findings_parts) == 1:
                findings = f"This is an abnormal study due to {findings_parts[0]}."
            else:
                findings = f"This is an abnormal study due to {' and '.join(findings_parts)}."
            
            if high_risk_findings:
                implications = []
                
                cognitive_metrics = ['button press accuracy', 'median reaction time', 'p3b latency', 'p3b amplitude']
                if any(metric in cognitive_metrics for metric in high_risk_findings):
                    implications.append("significantly reduced cognitive processing and attentional resources")
                
                sensory_metrics = ['p50 amplitude', 'n100 amplitude', 'p200 amplitude']
                if any(metric in sensory_metrics for metric in high_risk_findings):
                    implications.append("impaired sensory processing and gating mechanisms")
                
                if 'peak alpha frequency' in high_risk_findings:
                    implications.append("altered cortical arousal and attention networks")
                
                if implications:
                    findings += f" These findings suggest {', and '.join(implications)}."
                    findings += " This pattern is consistent with significant cognitive decline and warrants immediate clinical attention."
        
        return findings
    
    def extract_all_values(self, text: str) -> Dict:
        values = {}
        lines = [line.strip() for line in text.split('\n')]
        
        for i, line in enumerate(lines):
            if 'Button Press Accuracy' in line:
                numbers = re.findall(r'\d+\.?\d*', line)
                if numbers:
                    values['Button Press Accuracy'] = float(numbers[-1])
                elif i+1 < len(lines):
                    try:
                        next_line = lines[i+1].strip()
                        if ':' in next_line or any(word in next_line.lower() for word in ['normal', 'delayed', 'high', 'low', 'borderline']):
                            continue
                        numbers = re.findall(r'\d+\.?\d*', next_line)
                        if numbers:
                            values['Button Press Accuracy'] = float(numbers[0])
                    except ValueError:
                        pass
            
            if 'False Alarms' in line:
                numbers = re.findall(r'\d+\.?\d*', line)
                if numbers:
                    values['False Alarms'] = float(numbers[-1])
                elif i+1 < len(lines):
                    try:
                        next_line = lines[i+1].strip()
                        if ':' in next_line or any(word in next_line.lower() for word in ['normal', 'delayed', 'high', 'low', 'borderline']):
                            continue
                        numbers = re.findall(r'\d+\.?\d*', next_line)
                        if numbers:
                            values['False Alarms'] = float(numbers[0])
                    except ValueError:
                        pass
            
            if 'Median Reaction Time' in line:
                numbers = re.findall(r'\d+\.?\d*', line)
                if numbers:
                    values['Median Reaction Time'] = float(numbers[-1])
                elif i+1 < len(lines):
                    try:
                        next_line = lines[i+1].strip()
                        if ':' in next_line or any(word in next_line.lower() for word in ['normal', 'delayed', 'high', 'low', 'borderline']):
                            continue
                        numbers = re.findall(r'\d+\.?\d*', next_line)
                        if numbers:
                            values['Median Reaction Time'] = float(numbers[0])
                    except ValueError:
                        pass
        
        for i in range(len(lines) - 5):
            if lines[i] == 'P50' and i+1 < len(lines) and lines[i+1] == 'Standard':
                if i+2 < len(lines):
                    try:
                        values['P50 Amplitude'] = float(lines[i+2])
                    except ValueError:
                        pass
            
            if lines[i] == 'P3b' and i+1 < len(lines) and lines[i+1] == 'Target':
                if i+2 < len(lines) and i+3 < len(lines):
                    try:
                        values['P3b Amplitude'] = float(lines[i+2])
                        values['P3b Latency'] = float(lines[i+3])
                    except ValueError:
                        pass
            
            if lines[i] == 'Peak Alpha' and i+1 < len(lines):
                try:
                    values['Peak Alpha Frequency'] = float(lines[i+1])
                except ValueError:
                    pass
        
        return values
    
    def process_pdf(self, pdf_path: str) -> Dict:
        text = self.extract_pdf_text(pdf_path)
        if not text:
            return {"error": "Could not extract text from PDF"}
        
        values = self.extract_all_values(text)
        clinical_interpretations = {}
        
        for metric, value in values.items():
            clinical_interpretations[metric] = self.calculate_clinical_interpretation(metric, value)
        
        audiogram_data = self.extract_audiogram_data(text)
        
        generated_findings = self.generate_study_findings(values, clinical_interpretations, audiogram_data)
        
        return {
            'generated_study_findings': generated_findings,
            'extracted_values': values,
            'clinical_interpretations': clinical_interpretations,
            'audiogram_data': audiogram_data
        }
    
    def save_to_csv(self, results: Dict, output_file: str = 'medical_report_analysis.csv'):
        data = []
        
        values = results.get('extracted_values', {})
        clinical_interp = results.get('clinical_interpretations', {})
        
        for metric in sorted(set(values.keys()) | set(clinical_interp.keys())):
            range_info = self.clinical_ranges.get(metric, {})
            data.append({
                'Metric': metric,
                'Value': values.get(metric, 'Not found'),
                'Clinical_Interpretation': clinical_interp.get(metric, 'Not found'),
                'Normal_Reference': range_info.get('normal', 'N/A'),
                'Mild_AD_Reference': range_info.get('mild_ad', 'N/A'),
                'Risk_Level': clinical_interp.get(metric, 'Unknown')
            })
        
        df = pd.DataFrame(data)
        df.to_csv(output_file, index=False)
        print(f"Results saved to {output_file}")


def process_single_pdf(pdf_path: str):
    extractor = MedicalExtractor()
    
    try:
        results = extractor.process_pdf(pdf_path)
        extractor.save_to_csv(results)
        return results
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return None


if __name__ == "__main__":
    pdf_file = "Patient_30627.pdf"
    print("Medical PDF Extractor - Clinical Analysis")
    print("=" * 50)
    results = process_single_pdf(pdf_file)