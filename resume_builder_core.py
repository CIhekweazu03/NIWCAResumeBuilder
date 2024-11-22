import yaml
import os
import subprocess
from datetime import datetime
import boto3
import json
import sys
from botocore.exceptions import ClientError
import logging
from typing import Dict, List, Tuple, Optional, Union
from llm_enhancer import (
    generate_enhanced_experience,
    generate_enhanced_bio,
    generate_enhanced_activity
)

class ResumeBuilderCore:
    """
    Core functionality for building and processing resumes without UI components.
    Handles data processing, YAML generation, PDF creation, and S3 upload.
    """
    
    def __init__(self, s3_bucket: str = "niwc-generated-resumes"):
        """
        Initialize the resume builder with configuration.
        
        Args:
            s3_bucket (str): Name of the S3 bucket for storing generated resumes
        """
        self.S3_BUCKET_NAME = s3_bucket
        self.PDF_OUTPUT_PATH = "rendercv_output/pdf_outputs"
        self.YAML_OUTPUT_PATH = "yamlfiles"
        self.current_name = None
        
    def format_phone_number(self, phone: str) -> str:
        """
        Format phone number to international format.
        
        Args:
            phone (str): Input phone number
            
        Returns:
            str: Formatted phone number in +1XXXXXXXXXX format
        """
        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            digits = '1' + digits
        return '+' + digits
    
    def format_input_data(self, input_dict: dict) -> dict:
        """
        Converts the input dictionary format to the format expected by the resume builder.
        
        Args:
            input_dict (dict): Input data in the provided format
        
        Returns:
            dict: Data formatted for resume generation
        """
        resume_data = input_dict["resume"]
        applicant = input_dict["applicant"]
        user = input_dict["user"]
        
        formatted_data = {
            "personal_info": {
                "name": f"{user['firstName']} {user['lastName']}",
                "email": user["suiteEmail"],
                "phone": self.format_phone_number(user["phoneNumber"])
            },
            "bio": resume_data["biography"],
            "education": [],
            "experience": [],
            "activities": [],
            "skills": applicant["skillset"],
            "interests": applicant["interests"],
            "coursework": resume_data.get("courseWork", []),
            "accolades": resume_data.get("accolades", []),
            "certifications": []
        }
        
        # Format education
        for edu in resume_data.get("education", []):
            formatted_data["education"].append({
                "school": edu["name"],
                "type": edu["type"],
                "city": edu.get("location", "").split(",")[0].strip(),
                "state": edu.get("location", "").split(",")[1].strip() if "," in edu.get("location", "") else "",
                "gpa": float(edu["gpa"]) if "gpa" in edu else None,
                "gpa_max": float(edu["ofGPAMax"]) if "ofGPAMax" in edu else 4.0
            })
        
        # Format experience
        for exp in resume_data.get("experience", []):
            formatted_data["experience"].append({
                "job_title": exp["title"],
                "employer": exp["employer"],
                "location": exp["location"],
                "start_date": exp["start"].split("T")[0],
                "end_date": exp["end"].split("T")[0] if not exp["current"] else "",
                "current": exp["current"],
                "description": []
            })
        
        # Format activities
        for activity in resume_data.get("activities", []):
            formatted_data["activities"].append({
                "position": activity["position"],
                "activity_name": activity["title"],
                "start_date": activity["start"].split("T")[0],
                "end_date": activity["end"].split("T")[0] if not activity["current"] else "",
                "current": activity["current"],
                "description": []
            })
        
        # Format certifications
        for cert in resume_data.get("certifications", []):
            formatted_data["certifications"].append(
                f"{cert['title']} ({cert['completionYear']})"
            )
        
        return formatted_data

    def sanitize_resume_data(self, data: Union[Dict, List, str]) -> Union[Dict, List, str]:
        """
        Recursively sanitize resume data by escaping special LaTeX characters.
        
        Args:
            data: Input data to sanitize
            
        Returns:
            Sanitized version of the input data
        """
        if isinstance(data, dict):
            return {key: self.sanitize_resume_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self.sanitize_resume_data(item) for item in data]
        elif isinstance(data, str):
            return data.replace('$', '\\$')
        return data

    def generate_resume_yaml(self, resume_data: Dict, theme: str) -> str:
        """
        Convert resume data to RenderCV YAML format.
        
        Args:
            resume_data (dict): Resume data in standardized format
            theme (str): Theme to use for the resume
            
        Returns:
            str: YAML formatted string
        """
        cv_data = {
            "cv": {
                "name": resume_data["personal_info"]["name"],
                "email": resume_data["personal_info"]["email"],
                "phone": resume_data["personal_info"]["phone"],
                "sections": {}
            },
            "design": {
                "theme": theme
            }
        }
        
        if theme != "moderncv":
            cv_data["design"]["disable_last_updated_date"] = True
            
        # Add sections if they exist in resume_data
        if resume_data.get("bio"):
            cv_data["cv"]["sections"]["summary"] = [resume_data["bio"]]
            
        if resume_data.get("education"):
            education_list = []
            for edu in resume_data["education"]:
                if edu["school"]:
                    education_entry = {
                        "institution": edu["school"],
                        "area": edu["type"]
                    }
                    
                    if edu.get("city") and edu.get("state"):
                        location_parts = []
                        if edu.get("address"):
                            location_parts.append(edu["address"])
                        location_parts.extend([edu["city"], edu["state"]])
                        if edu.get("zip"):
                            location_parts.append(edu["zip"])
                        education_entry["location"] = ", ".join(location_parts)
                    
                    if edu.get("gpa"):
                        education_entry["highlights"] = [
                            f"GPA: {edu['gpa']}/{edu['gpa_max']}"
                        ]
                    
                    education_list.append(education_entry)
            
            if education_list:
                cv_data["cv"]["sections"]["education"] = education_list
        
        if resume_data.get("experience"):
            experience_list = []
            for exp in resume_data["experience"]:
                exp_entry = {
                    "position": exp["job_title"],
                    "company": exp["employer"],
                    "location": exp["location"],
                    "start_date": exp["start_date"],
                    "end_date": "present" if exp["current"] else exp["end_date"],
                    "highlights": exp["description"]
                }
                experience_list.append(exp_entry)
            cv_data["cv"]["sections"]["experience"] = experience_list
            
        # Add activities section
        if resume_data.get("activities"):
            activities_list = []
            for activity in resume_data["activities"]:
                activity_entry = {
                    "company": activity["activity_name"],
                    "position": activity["position"],
                    "start_date": activity["start_date"],
                    "end_date": "present" if activity["current"] else activity["end_date"],
                    "highlights": activity["description"]
                }
                activities_list.append(activity_entry)
            cv_data["cv"]["sections"]["activities"] = activities_list
        
        # Add other sections with bullet points
        for section in ["skills", "coursework", "certifications", "interests", "accolades"]:
            if resume_data.get(section):
                cv_data["cv"]["sections"][section] = [
                    f"• {item}" for item in resume_data[section]
                ]
        
        return yaml.dump(cv_data, sort_keys=False, allow_unicode=True)

    def save_resume_yaml(self, yaml_content: str, name: str, theme: str, timestamp: str) -> str:
        """
        Save YAML content to a file.
        
        Args:
            yaml_content (str): YAML content to save
            name (str): Person's name
            theme (str): Resume theme
            timestamp (str): Timestamp for filename
            
        Returns:
            str: Name of the saved file
        """
        os.makedirs(self.YAML_OUTPUT_PATH, exist_ok=True)
        formatted_name = "".join(x for x in name if x.isalnum())
        filename = f"{formatted_name}_{timestamp}_resume_{theme}_CV.yaml"
        filepath = os.path.join(self.YAML_OUTPUT_PATH, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        return filename

    def create_render_script(self, name: str, timestamp: str) -> Tuple[str, str]:
        """
        Create script to render YAML files into PDFs.
        
        Args:
            name (str): Person's name
            timestamp (str): Timestamp for filenames
            
        Returns:
            tuple: (script_path, output_dir)
        """
        formatted_name = "".join(x for x in name if x.isalnum())
        output_dir = os.path.abspath(self.PDF_OUTPUT_PATH)
        yaml_dir = os.path.abspath(self.YAML_OUTPUT_PATH)
        
        script_content = f"""#!/bin/bash
set -e
mkdir -p "{output_dir}"

for theme in classic moderncv sb2nov engineeringresumes; do
    yaml_path="{yaml_dir}/{formatted_name}_{timestamp}_resume_${{theme}}_CV.yaml"
    if [ ! -f "$yaml_path" ]; then
        echo "YAML file not found: $yaml_path"
        continue
    fi
    
    mkdir -p "{output_dir}/$theme"
    rendercv render "$yaml_path" --output-folder-name "{output_dir}/$theme"
    
    pdf_file=$(find "{output_dir}/$theme" -type f -name "*.pdf")
    if [ -n "$pdf_file" ]; then
        mv "$pdf_file" "{output_dir}/${{theme}}_$(basename "$pdf_file")"
        rm -r "{output_dir}/$theme"
    fi
done
"""
        script_name = f"rendercv_script_{formatted_name}_{timestamp}.sh"
        script_path = os.path.abspath(script_name)
        
        with open(script_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        return script_path, output_dir
    
    def run_render_script(self, script_path: str) -> Tuple[bool, str, List[str]]:
        """
        Execute render script and track generated PDFs.
        
        Args:
            script_path (str): Path to the render script
            
        Returns:
            Tuple[bool, str, List[str]]: 
                - Success status
                - Error message (empty if successful)
                - List of generated PDF filenames
        """
        try:
            # Clean up old YAML files
            yaml_dir = os.path.abspath(self.YAML_OUTPUT_PATH)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_yamls = set()
            
            # Get list of current YAML files to keep
            for theme in ["classic", "moderncv", "sb2nov", "engineeringresumes"]:
                current_yamls.add(os.path.join(yaml_dir, f"{self.current_name}_{timestamp}_resume_{theme}_CV.yaml"))
            
            # Remove old YAML files
            for file in os.listdir(yaml_dir):
                file_path = os.path.join(yaml_dir, file)
                if file_path not in current_yamls and file.endswith('.yaml'):
                    os.remove(file_path)

            # Ensure output directory exists and is empty
            output_dir = os.path.abspath(self.PDF_OUTPUT_PATH)
            os.makedirs(output_dir, exist_ok=True)
            
            # Clean output directory before generating new PDFs
            for file in os.listdir(output_dir):
                if file.endswith('.pdf'):
                    os.remove(os.path.join(output_dir, file))

            # Run render script
            process = subprocess.run(
                f'/bin/bash "{script_path}"',
                shell=True,
                capture_output=True,
                text=True,
                check=False
            )
            
            if process.returncode != 0:
                return False, process.stderr, []

            # Get all PDFs in output directory - these are all new since we cleaned the directory
            new_pdfs = [f for f in os.listdir(output_dir) if f.endswith('.pdf')]
            
            # Verify we have the expected number of PDFs
            if len(new_pdfs) != 4:  # We expect exactly 4 PDFs (one for each theme)
                return False, f"Expected 4 PDFs, but found {len(new_pdfs)}", []
                
            return True, "", new_pdfs
            
        except Exception as e:
            return False, str(e), []

    def upload_pdfs_to_s3(
        self,
        pdf_directory: str,
        pdf_files: List[str],
        user_name: str,
        user_email: str
    ) -> Tuple[bool, Dict[str, str], str]:
        """
        Upload only the PDFs generated in the current run to S3 bucket.
        
        Args:
            pdf_directory (str): Local directory containing the PDF files
            pdf_files (List[str]): List of PDF filenames from current run
            user_name (str): Username for folder name
            user_email (str): User email for folder organization
            
        Returns:
            Tuple[bool, Dict[str, str], str]: 
                - Success status
                - Dictionary mapping PDF filenames to their S3 URIs
                - Error message (empty string if successful)
        """
        try:
            if not pdf_files:
                return False, {}, "No PDF files provided for upload"
                
            s3_client = boto3.client('s3')
            pdf_uris = {}
            
            # Create folder name from user info
            folder_name = f"{user_name}_{user_email}".lower()
            folder_name = "".join(c if c.isalnum() or c == '_' or c == '-' else '_' 
                                for c in folder_name)
            
            # Print debug info
            print(f"Attempting to upload {len(pdf_files)} PDFs from {pdf_directory}")
            for pdf_file in pdf_files:
                local_file_path = os.path.join(pdf_directory, pdf_file)
                print(f"Checking file: {local_file_path}")
                
                # Verify file exists before attempting upload
                if not os.path.exists(local_file_path):
                    print(f"File not found: {local_file_path}")
                    continue
                
                try:
                    # Construct S3 key with user's folder
                    s3_key = f"resumes/{folder_name}/{pdf_file}"
                    
                    # Upload file with metadata
                    s3_client.upload_file(
                        local_file_path,
                        self.S3_BUCKET_NAME,
                        s3_key,
                        ExtraArgs={
                            'ContentType': 'application/pdf',
                            'ContentDisposition': f'inline; filename="{pdf_file}"',
                            'Metadata': {
                                'username': user_name,
                                'email': user_email,
                                'upload_timestamp': datetime.now().isoformat()
                            }
                        }
                    )
                    
                    # Store S3 URI for the uploaded file
                    uri = f"s3://{self.S3_BUCKET_NAME}/{s3_key}"
                    pdf_uris[pdf_file] = uri
                    print(f"Successfully uploaded: {pdf_file} to {uri}")
                    
                except ClientError as e:
                    print(f"Failed to upload {pdf_file}: {str(e)}")
                    continue
                
            if not pdf_uris:
                return False, {}, "No PDF files were successfully uploaded"
                
            return True, pdf_uris, ""
            
        except Exception as e:
            return False, {}, f"An unexpected error occurred during S3 upload: {str(e)}"

    def build_resume(self, input_data: Dict) -> List[str]:
        """
        Main function to build resume from input data and return S3 URIs.
        
        Args:
            input_data (dict): Resume data
                    
        Returns:
            List[str]: List of S3 URIs for the generated PDFs
        """
        try:
            self.current_name = "".join(x for x in input_data["personal_info"]["name"] if x.isalnum())
            
            # Format phone number
            input_data["personal_info"]["phone"] = self.format_phone_number(
                input_data["personal_info"]["phone"]
            )
            
            # Enhance content using LLM
            if input_data.get("bio"):
                input_data["bio"] = generate_enhanced_bio(input_data["bio"])
            
            if input_data.get("experience"):
                for exp in input_data["experience"]:
                    if exp.get("description"):
                        description_text = "\n".join(exp["description"])
                        exp["description"] = generate_enhanced_experience(
                            description_text
                        ).split('\n')
            
            if input_data.get("activities"):
                for activity in input_data["activities"]:
                    if activity.get("description"):
                        description_text = "\n".join(activity["description"])
                        activity["description"] = generate_enhanced_activity(
                            description_text
                        ).split('\n')
            
            # Sanitize data
            input_data = self.sanitize_resume_data(input_data)
            
            # Generate timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Generate and save YAML files for each theme
            themes = ["classic", "moderncv", "sb2nov", "engineeringresumes"]
            yaml_files = []
            for theme in themes:
                yaml_content = self.generate_resume_yaml(input_data, theme)
                filename = self.save_resume_yaml(
                    yaml_content,
                    input_data["personal_info"]["name"],
                    theme,
                    timestamp
                )
                yaml_files.append(filename)
            
            # Create and run render script
            script_path, output_dir = self.create_render_script(
                input_data["personal_info"]["name"],
                timestamp
            )
            success, script_output, new_pdfs = self.run_render_script(script_path)
            
            if not success:
                raise Exception(f"PDF generation failed: {script_output}")
                
            print(f"Generated PDFs: {new_pdfs}")
            
            # Upload only the new PDFs to S3
            success, uri_map, error = self.upload_pdfs_to_s3(
                output_dir,
                new_pdfs,
                input_data["personal_info"]["name"],
                input_data["personal_info"]["email"]
            )
            
            if not success:
                raise Exception(f"S3 upload failed: {error}")
            
            return list(uri_map.values())
            
        except Exception as e:
            raise Exception(f"Resume building failed: {str(e)}")
        
def main():
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Missing input data"}))
        sys.exit(1)
        
    try:
        input_json = json.loads(sys.argv[1])
        builder = ResumeBuilderCore()
        formatted_data = builder.format_input_data(input_json)
        s3_uris = builder.build_resume(formatted_data)
        print(json.dumps({"s3_uris": s3_uris}))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()