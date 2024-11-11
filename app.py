import streamlit as st
from datetime import datetime
import yaml
import pandas as pd
import os
import subprocess
from llm_enhancer import (
    generate_enhanced_experience,
    generate_enhanced_bio,
    generate_enhanced_activity
)

st.set_page_config(
    page_title="Resume Builder",
    page_icon="NIWC_Atlantic_Logo.jpg"
)

def create_experience_section(key_prefix):
    col1, col2 = st.columns(2)
    with col1:
        job_title = st.text_input("Job Title*", key=f"{key_prefix}_job_title")
        employer = st.text_input("Employer*", key=f"{key_prefix}_employer")
        start_date = st.date_input("Start Date*", key=f"{key_prefix}_start_date")
    with col2:
        current = st.selectbox("Current Position?", ["Yes", "No"], key=f"{key_prefix}_current")
        end_date = None if current == "Yes" else st.date_input(
            "End Date*", 
            min_value=start_date,
            key=f"{key_prefix}_end_date"
        )
        location = st.text_input("Location*", key=f"{key_prefix}_location")
    
    # Add description field with help text
    st.write("Description* (Enter each bullet point on a new line)")
    description = st.text_area(
        "Experience Description", 
        key=f"{key_prefix}_description",
        help="Enter each accomplishment or responsibility on a new line. These will be converted to bullet points."
    )
    
    return {
        "job_title": job_title,
        "employer": employer,
        "start_date": start_date,
        "current": current == "Yes",
        "end_date": end_date,
        "location": location,
        "description": description.split('\n') if description else []  # Split into list by newlines
    }

def enhance_experience_descriptions(experience_sections):
    """
    Enhance the description for each experience section using the LLM.
    """
    enhanced_sections = []
    for exp in experience_sections:
        if exp["description"]:
            # Join the description bullets into a string for enhancement
            description_text = "\n".join(f"- {bullet}" for bullet in exp["description"] if bullet.strip())
            # Get enhanced description
            enhanced_description = generate_enhanced_experience(description_text)
            # Split enhanced description back into bullets, removing empty lines
            enhanced_bullets = [
                line[2:] if line.startswith('- ') else line 
                for line in enhanced_description.split('\n')
                if line.strip()
            ]
            # Create new experience dict with enhanced description
            enhanced_exp = exp.copy()
            enhanced_exp["description"] = enhanced_bullets
            enhanced_sections.append(enhanced_exp)
        else:
            enhanced_sections.append(exp)
    return enhanced_sections

def create_education_section(key_prefix):
    col1, col2 = st.columns(2)
    with col1:
        school = st.text_input("School Name", key=f"{key_prefix}_school")
        edu_type = st.selectbox(
            "Education Type",
            ["High School", "Undergraduate", "Graduate", "Doctoral Studies"],
            key=f"{key_prefix}_type"
        )
    with col2:
        gpa = st.number_input("GPA", min_value=0.0, max_value=10.0, step=0.1, key=f"{key_prefix}_gpa")
        gpa_max = st.number_input("GPA Max", min_value=0.0, max_value=10.0, step=0.1, value=4.0, key=f"{key_prefix}_gpa_max")
    
    address = st.text_input("Address", key=f"{key_prefix}_address")
    col3, col4, col5 = st.columns(3)
    with col3:
        city = st.text_input("City", key=f"{key_prefix}_city")
    with col4:
        state = st.text_input("State", key=f"{key_prefix}_state")
    with col5:
        zip_code = st.text_input("ZIP", key=f"{key_prefix}_zip")
    
    return {
        "school": school,
        "type": edu_type,
        "gpa": gpa,
        "gpa_max": gpa_max,
        "address": address,
        "city": city,
        "state": state,
        "zip": zip_code
    }

def create_activity_section(key_prefix):
    col1, col2 = st.columns(2)
    with col1:
        position = st.text_input("Position*", key=f"{key_prefix}_position")
        activity_name = st.text_input("Activity Name*", key=f"{key_prefix}_name")
        start_date = st.date_input("Start Date*", key=f"{key_prefix}_start_date")
    with col2:
        current = st.selectbox("Current Activity?", ["Yes", "No"], key=f"{key_prefix}_current")
        end_date = None if current == "Yes" else st.date_input(
            "End Date*",
            min_value=start_date,
            key=f"{key_prefix}_end_date"
        )
    
    # Add description field with help text
    st.write("Description* (Enter each bullet point on a new line)")
    description = st.text_area(
        "Activity Description", 
        key=f"{key_prefix}_description",
        help="Enter each responsibility or achievement on a new line. These will be converted to bullet points."
    )
    
    return {
        "position": position,
        "activity_name": activity_name,
        "start_date": start_date,
        "current": current == "Yes",
        "end_date": end_date,
        "description": description.split('\n') if description else []  # Split into list by newlines
    }

def enhance_activity_descriptions(activity_sections):
    """
    Enhance the description for each activity section using the LLM.
    """
    enhanced_sections = []
    for activity in activity_sections:
        if activity["description"]:
            # Join the description bullets into a string for enhancement
            description_text = "\n".join(f"- {bullet}" for bullet in activity["description"] if bullet.strip())
            # Get enhanced description
            enhanced_description = generate_enhanced_activity(description_text)
            # Split enhanced description back into bullets, removing empty lines
            enhanced_bullets = [
                line[2:] if line.startswith('- ') else line 
                for line in enhanced_description.split('\n')
                if line.strip()
            ]
            # Create new activity dict with enhanced description
            enhanced_activity = activity.copy()
            enhanced_activity["description"] = enhanced_bullets
            enhanced_sections.append(enhanced_activity)
        else:
            enhanced_sections.append(activity)
    return enhanced_sections


def generate_resume_yaml(resume_data, theme):
    """
    Convert resume form data to RenderCV YAML format for a specific theme.
    
    Args:
        resume_data (dict): The resume data collected from the Streamlit form
        theme (str): The theme to use for the resume
        
    Returns:
        str: YAML formatted string
    """
    # Basic CV structure
    enhanced_bio = generate_enhanced_bio(resume_data["bio"]) if resume_data.get("bio") else None
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
    
    # Add disable_last_updated_date only for non-moderncv themes
    if theme != "moderncv":
        cv_data["design"]["disable_last_updated_date"] = True
    
    # Add summary/bio section
    if resume_data.get("bio"):
        cv_data["cv"]["sections"]["summary"] = [enhanced_bio]
    
    # Add education section if it exists
    if resume_data.get("education"):
        education_list = []
        for edu in resume_data["education"]:
            if edu["school"]:  # Only add if school name exists
                education_entry = {
                    "institution": edu["school"],
                    "area": edu["type"]
                }
                
                # Add location if city and state exist
                if edu.get("city") and edu.get("state"):
                    location_parts = []
                    if edu.get("address"):
                        location_parts.append(edu["address"])
                    location_parts.extend([edu["city"], edu["state"]])
                    if edu.get("zip"):
                        location_parts.append(edu["zip"])
                    education_entry["location"] = ", ".join(location_parts)
                
                # Add GPA as a highlight if it exists
                if edu.get("gpa"):
                    education_entry["highlights"] = [
                        f"GPA: {edu['gpa']}/{edu['gpa_max']}"
                    ]
                
                education_list.append(education_entry)
        
        if education_list:  # Only add education section if there are valid entries
            cv_data["cv"]["sections"]["education"] = education_list
    
    # Add experience section
    if resume_data.get("experience"):
        experience_list = []
        for exp in resume_data["experience"]:
            exp_entry = {
                "position": exp["job_title"],
                "company": exp["employer"],
                "location": exp["location"],
                "start_date": exp["start_date"].strftime("%Y-%m-%d"),
                "end_date": "present" if exp["current"] else exp["end_date"].strftime("%Y-%m-%d"),
                "highlights": exp["description"]  # Add description points as highlights
            }
            experience_list.append(exp_entry)
        
        cv_data["cv"]["sections"]["experience"] = experience_list
    
    # Add skills as technologies section if it exists
    if resume_data.get("skills"):
        tech_entries = []
        # Group all skills under a single "Skills" label
        if resume_data["skills"]:
            tech_entries.append({
                "label": "Skills",
                "details": ", ".join(resume_data["skills"])
            })
        
    
    # Add activities section if it exists
    if resume_data.get("activities"):
        activities_list = []
        for activity in resume_data["activities"]:
            activity_entry = {
                "company": activity["activity_name"],
                "position": activity["position"],
                "start_date": activity["start_date"].strftime("%Y-%m-%d"),
                "end_date": "present" if activity["current"] else activity["end_date"].strftime("%Y-%m-%d"),
                "highlights": activity["description"]  # Add description points as highlights
            }
            activities_list.append(activity_entry)
        
        if activities_list:
            cv_data["cv"]["sections"]["activities"] = activities_list
    
    # Add other sections with bullet points
    if resume_data.get("skills"):
        cv_data["cv"]["sections"]["skills"] = [f"• {skill}" for skill in resume_data["skills"]]
    
    if resume_data.get("coursework"):
        cv_data["cv"]["sections"]["coursework"] = [f"• {course}" for course in resume_data["coursework"]]
    
    if resume_data.get("certifications"):
        cv_data["cv"]["sections"]["certifications"] = [f"• {cert}" for cert in resume_data["certifications"]]
    
    if resume_data.get("interests"):
        cv_data["cv"]["sections"]["interests"] = [f"• {interest}" for interest in resume_data["interests"]]
    
    if resume_data.get("accolades"):
        cv_data["cv"]["sections"]["accolades"] = [f"• {accolade}" for accolade in resume_data["accolades"]]
    
    # Convert to YAML
    return yaml.dump(cv_data, sort_keys=False, allow_unicode=True)

def save_resume_yaml(yaml_content, name, theme, timestamp):
    """
    Save the YAML content to a file in the yamlfiles subfolder.
    
    Args:
        yaml_content (str): The YAML content to save
        name (str): The name of the person
        theme (str): The theme used for the resume
        timestamp (str): The timestamp to use in the filename
        
    Returns:
        str: The name of the saved file
    """
    # Create yamlfiles directory if it doesn't exist
    yaml_dir = os.path.abspath('yamlfiles')
    if not os.path.exists(yaml_dir):
        os.makedirs(yaml_dir)
        print(f"Created directory: {yaml_dir}")
    
    # Format name (remove spaces and special characters)
    formatted_name = "".join(x for x in name if x.isalnum())
    
    # Create filename with user details
    filename = f"{formatted_name}_{timestamp}_resume_{theme}_CV.yaml"
    filepath = os.path.join(yaml_dir, filename)
    
    # Save the file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        print(f"Successfully saved YAML file: {filepath}")
        
        # Verify file exists and has content
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"File exists with size: {size} bytes")
        else:
            print(f"WARNING: File was not created: {filepath}")
            
    except Exception as e:
        print(f"Error saving YAML file: {str(e)}")
        raise
    
    return filename

def create_render_script(name, timestamp):
    """
    Creates a bash script to render the YAML files into PDFs using RenderCV.
    
    Args:
        name (str): The name of the person
        timestamp (str): The timestamp used in the filenames
    
    Returns:
        tuple: (script_name, output_dir) where script_name is the path to the created script
               and output_dir is the directory where PDFs will be saved
    """
    # Format name for filenames
    formatted_name = "".join(x for x in name if x.isalnum())
    
    # Create output directory path using absolute path
    output_dir = os.path.abspath("rendercv_output/pdf_outputs")
    
    # Current working directory for relative paths
    current_dir = os.path.abspath(os.getcwd())
    yaml_dir = os.path.join(current_dir, "yamlfiles")
    
    script_content = f"""#!/bin/bash
set -e  # Exit on error

# Echo commands for debugging
set -x

# Create base output directory
mkdir -p "{output_dir}"

echo "Created output directory: {output_dir}"

# Debug: List yaml files
echo "Contents of yaml directory:"
ls -la "{yaml_dir}"

# Process each theme
for theme in classic moderncv sb2nov engineeringresumes; do
    echo "Processing theme: $theme"
    
    # Construct input YAML path
    yaml_path="{yaml_dir}/{formatted_name}_{timestamp}_resume_${{theme}}_CV.yaml"
    echo "Looking for YAML file: $yaml_path"
    
    # Check if YAML file exists
    if [ ! -f "$yaml_path" ]; then
        echo "ERROR: YAML file not found: $yaml_path"
        continue
    fi
    
    # Create theme-specific directory
    mkdir -p "{output_dir}/$theme"
    
    # Run rendercv command
    rendercv render "$yaml_path" --output-folder-name "{output_dir}/$theme"
    
    # Move and rename the generated PDF
    pdf_file=$(find "{output_dir}/$theme" -type f -name "*.pdf")
    if [ -n "$pdf_file" ]; then
        mv "$pdf_file" "{output_dir}/${{theme}}_$(basename "$pdf_file")"
        rm -r "{output_dir}/$theme"
    else
        echo "No PDF found for theme: $theme"
    fi
done

echo "PDF generation complete. Files are available in: {output_dir}"
"""
    
    # Create script with timestamp
    script_name = f"rendercv_script_{formatted_name}_{timestamp}.sh"
    script_path = os.path.abspath(script_name)
    
    # Write script with Unix line endings
    with open(script_path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(script_content)
    
    # Make script executable
    os.chmod(script_path, 0o755)
    
    return script_path, output_dir

def run_render_script(script_path):
    """
    Executes the generated render script and captures its output.
    
    Args:
        script_path (str): Path to the render script
    
    Returns:
        tuple: (success, output) where success is a boolean indicating if the script ran successfully
               and output is the script's output/error message
    """
    try:
        # Run script with shell=True to ensure proper bash interpretation
        # Capture both stdout and stderr
        process = subprocess.run(
            f'/bin/bash "{script_path}"',
            shell=True,
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        
        # Combine stdout and stderr for comprehensive output
        output = f"STDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}"
        
        # Check if the process was successful
        if process.returncode == 0:
            return True, output
        else:
            return False, f"Script failed with exit code {process.returncode}\n{output}"
            
    except Exception as e:
        return False, f"Error executing script: {str(e)}"

def sanitize_resume_data(data):
    """
    Recursively sanitize resume data by escaping special LaTeX characters.
    Currently handles '$' by replacing it with '\$'.
    
    Args:
        data: Can be a dictionary, list, or string containing resume data
        
    Returns:
        The sanitized version of the input data with the same structure
    """
    if isinstance(data, dict):
        return {key: sanitize_resume_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_resume_data(item) for item in data]
    elif isinstance(data, str):
        # Replace dollar signs with escaped version
        # Using replace() instead of regex for simplicity and performance
        return data.replace('$', '\\$')
    else:
        # Return unchanged if not a string, list, or dict
        return data

def main():

    # Initialize session state for generated files if not exists
    if 'generated_files' not in st.session_state:
        st.session_state.generated_files = None
    if 'output_dir' not in st.session_state:
        st.session_state.output_dir = None
    if 'saved_yaml_files' not in st.session_state:
        st.session_state.saved_yaml_files = None

    # Add these new initializations
    if "temp_experience" not in st.session_state:
        st.session_state.temp_experience = {}
    if "experiences" not in st.session_state:
        st.session_state.experiences = []
    if "temp_education" not in st.session_state:
        st.session_state.temp_education = {}
    if "educations" not in st.session_state:
        st.session_state.educations = []
    if "temp_activity" not in st.session_state:
        st.session_state.temp_activity = {}
    if "activities" not in st.session_state:
        st.session_state.activities = []

    st.title("Resume Builder")
    
    # Welcome message
    st.write("""
    Welcome to the Resume Builder! This tool will help you create a professional resume.
    
    **Required fields**: Name, Email, Phone Number, Short Bio, and at least one complete Work Experience.
    All other sections are optional and can be added as needed.
    
    Fields marked with * are required within their respective sections.
    """)
    
    # Personal Information
    st.header("Personal Information")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name*")
        email = st.text_input("Email*")
    with col2:
        phone = st.text_input("Phone Number*\n\n(Please put phone number in the format of national code and then number i.e. a US number (803)-123-4567 should be in the format +18035555555)")
    
    st.header("Short Bio")
    bio = st.text_area("Tell us about yourself*")
    
    # Education
    st.header("Education (Optional)")
    
    # Form for adding new education
    with st.expander("Add New Education"):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.temp_education["school"] = st.text_input("School Name", key="new_edu_school")
            st.session_state.temp_education["type"] = st.selectbox(
                "Education Type",
                ["High School", "Undergraduate", "Graduate", "Doctoral Studies"],
                key="new_edu_type"
            )
        with col2:
            st.session_state.temp_education["gpa"] = st.number_input("GPA", min_value=0.0, max_value=10.0, step=0.1, key="new_edu_gpa")
            st.session_state.temp_education["gpa_max"] = st.number_input("GPA Max", min_value=0.0, max_value=10.0, step=0.1, value=4.0, key="new_edu_gpa_max")
        
        st.session_state.temp_education["address"] = st.text_input("Address", key="new_edu_address")
        col3, col4, col5 = st.columns(3)
        with col3:
            st.session_state.temp_education["city"] = st.text_input("City", key="new_edu_city")
        with col4:
            st.session_state.temp_education["state"] = st.text_input("State", key="new_edu_state")
        with col5:
            st.session_state.temp_education["zip"] = st.text_input("ZIP", key="new_edu_zip")

        if st.button("Add Education"):
            if st.session_state.temp_education["school"]:
                st.session_state.educations.append(dict(st.session_state.temp_education))
                st.session_state.temp_education = {}
                st.rerun()
            else:
                st.error("Please enter at least the school name.")

    # Display existing education entries
    if st.session_state.educations:
        st.subheader("Added Education")
        for idx, edu in enumerate(st.session_state.educations):
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{edu['school']} - {edu['type']}**")
                    if edu['gpa']:
                        st.write(f"GPA: {edu['gpa']}/{edu['gpa_max']}")
                    address_parts = [p for p in [edu['address'], edu['city'], edu['state'], edu['zip']] if p]
                    if address_parts:
                        st.write(", ".join(address_parts))
                with col2:
                    if st.button(f"Delete", key=f"del_edu_{idx}"):
                        st.session_state.educations.pop(idx)
                        st.rerun()
                st.divider()
    
    # Skills
    st.header("Skills (Optional)")
    if "skills" not in st.session_state:
        st.session_state.skills = []
    
    new_skill = st.text_input("Add Skill")
    if st.button("Add Skill"):
        if new_skill:
            st.session_state.skills.append(new_skill)
            st.rerun()
    
    for i, skill in enumerate(st.session_state.skills):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(skill)
        with col2:
            if st.button(f"Delete", key=f"del_skill_{i}"):
                st.session_state.skills.pop(i)
                st.rerun()
    
    # Interests
    st.header("Interests (Optional)")
    if "interests" not in st.session_state:
        st.session_state.interests = []
    
    new_interest = st.text_input("Add Interest")
    if st.button("Add Interest"):
        if new_interest:
            st.session_state.interests.append(new_interest)
            st.rerun()
    
    for i, interest in enumerate(st.session_state.interests):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(interest)
        with col2:
            if st.button(f"Delete", key=f"del_interest_{i}"):
                st.session_state.interests.pop(i)
                st.rerun()
    
    # Coursework
    st.header("Coursework (Optional)")
    if "coursework" not in st.session_state:
        st.session_state.coursework = []
    
    new_course = st.text_input("Add Coursework")
    if st.button("Add Course"):
        if new_course:
            st.session_state.coursework.append(new_course)
    
    for i, course in enumerate(st.session_state.coursework):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(course)
        with col2:
            if st.button(f"Delete", key=f"del_course_{i}"):
                st.session_state.coursework.pop(i)
                st.rerun()
    
    # Certifications
    st.header("Certifications (Optional)")
    if "certifications" not in st.session_state:
        st.session_state.certifications = []
    
    new_cert = st.text_input("Add Certification")
    if st.button("Add Certification"):
        if new_cert:
            st.session_state.certifications.append(new_cert)
    
    for i, cert in enumerate(st.session_state.certifications):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(cert)
        with col2:
            if st.button(f"Delete", key=f"del_cert_{i}"):
                st.session_state.certifications.pop(i)
                st.rerun()
    
    # Accolades
    st.header("Accolades (Optional)")
    if "accolades" not in st.session_state:
        st.session_state.accolades = []
    
    new_accolade = st.text_input("Add Accolade")
    if st.button("Add Accolade"):
        if new_accolade:
            st.session_state.accolades.append(new_accolade)
    
    for i, accolade in enumerate(st.session_state.accolades):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(accolade)
        with col2:
            if st.button(f"Delete", key=f"del_accolade_{i}"):
                st.session_state.accolades.pop(i)
                st.rerun()
    
    # Experience
    st.header("Work Experience")
    st.write("At least one complete work experience is required.")
    
    # Form for adding new experience
    with st.expander("Add New Experience", expanded=not st.session_state.experiences):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.temp_experience["job_title"] = st.text_input("Job Title*", key="new_exp_title")
            st.session_state.temp_experience["employer"] = st.text_input("Employer*", key="new_exp_employer")
            st.session_state.temp_experience["start_date"] = st.date_input("Start Date*", key="new_exp_start")
        with col2:
            current = st.selectbox("Current Position?", ["Yes", "No"], key="new_exp_current")
            st.session_state.temp_experience["current"] = current == "Yes"
            if not st.session_state.temp_experience["current"]:
                st.session_state.temp_experience["end_date"] = st.date_input(
                    "End Date*",
                    min_value=st.session_state.temp_experience["start_date"],
                    key="new_exp_end"
                )
            st.session_state.temp_experience["location"] = st.text_input("Location*", key="new_exp_location")
        
        st.write("Description* (Enter each bullet point on a new line)")
        description = st.text_area(
            "Experience Description",
            key="new_exp_description",
            help="Enter each accomplishment or responsibility on a new line. These will be converted to bullet points."
        )
        st.session_state.temp_experience["description"] = description.split('\n') if description else []

        if st.button("Add Experience"):
            if (st.session_state.temp_experience["job_title"] and 
                st.session_state.temp_experience["employer"] and 
                st.session_state.temp_experience["location"] and 
                st.session_state.temp_experience["description"]):
                
                # Add the current experience to the list
                st.session_state.experiences.append(dict(st.session_state.temp_experience))
                # Clear the temporary experience
                st.session_state.temp_experience = {}
                st.rerun()
            else:
                st.error("Please fill in all required fields.")

    # Display existing experiences
    if st.session_state.experiences:
        st.subheader("Added Experiences")
        for idx, exp in enumerate(st.session_state.experiences):
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{exp['job_title']} at {exp['employer']}**")
                    st.write(f"Location: {exp['location']}")
                    st.write(f"Duration: {exp['start_date']} - {'Present' if exp['current'] else exp['end_date']}")
                    for bullet in exp['description']:
                        if bullet.strip():  # Only display non-empty bullets
                            st.write(f"• {bullet}")
                with col2:
                    if len(st.session_state.experiences) > 1 or idx > 0:  # Allow deletion only if not the last/only experience
                        if st.button(f"Delete", key=f"del_exp_{idx}"):
                            st.session_state.experiences.pop(idx)
                            st.rerun()
                st.divider()
    
    # Activities
    st.header("Activities (Optional)")
    
    # Form for adding new activity
    with st.expander("Add New Activity"):
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.temp_activity["position"] = st.text_input("Position*", key="new_act_position")
            st.session_state.temp_activity["activity_name"] = st.text_input("Activity Name*", key="new_act_name")
            st.session_state.temp_activity["start_date"] = st.date_input("Start Date*", key="new_act_start")
        with col2:
            current = st.selectbox("Current Activity?", ["Yes", "No"], key="new_act_current")
            st.session_state.temp_activity["current"] = current == "Yes"
            if not st.session_state.temp_activity["current"]:
                st.session_state.temp_activity["end_date"] = st.date_input(
                    "End Date*",
                    min_value=st.session_state.temp_activity["start_date"],
                    key="new_act_end"
                )

        st.write("Description* (Enter each bullet point on a new line)")
        description = st.text_area(
            "Activity Description",
            key="new_act_description",
            help="Enter each responsibility or achievement on a new line. These will be converted to bullet points."
        )
        st.session_state.temp_activity["description"] = description.split('\n') if description else []

        if st.button("Add Activity"):
            if (st.session_state.temp_activity["position"] and 
                st.session_state.temp_activity["activity_name"] and 
                st.session_state.temp_activity["description"]):
                
                st.session_state.activities.append(dict(st.session_state.temp_activity))
                st.session_state.temp_activity = {}
                st.rerun()
            else:
                st.error("Please fill in all required fields.")

    # Display existing activities
    if st.session_state.activities:
        st.subheader("Added Activities")
        for idx, activity in enumerate(st.session_state.activities):
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{activity['position']} at {activity['activity_name']}**")
                    st.write(f"Duration: {activity['start_date']} - {'Present' if activity['current'] else activity['end_date']}")
                    for bullet in activity['description']:
                        if bullet.strip():  # Only display non-empty bullets
                            st.write(f"• {bullet}")
                with col2:
                    if st.button(f"Delete", key=f"del_act_{idx}"):
                        st.session_state.activities.pop(idx)
                        st.rerun()
                st.divider()

    if st.button("Generate Resumes"):
        if not name or not email or not phone or not bio or not st.session_state.experiences:
            st.error("Please fill in all required fields...")
        else:
            # Show a loading message while processing
            with st.spinner("Enhancing resume content and generating PDFs..."):
                try:
                    # Generate single timestamp for all files
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Create resume data dictionary
                    resume_data = {
                        "personal_info": {
                            "name": name,
                            "email": email,
                            "phone": phone
                        },
                        "bio": bio,
                        "education": st.session_state.educations,
                        "skills": st.session_state.skills,
                        "interests": st.session_state.interests,
                        "coursework": st.session_state.coursework,
                        "certifications": st.session_state.certifications,
                        "accolades": st.session_state.accolades,
                        "experience": enhance_experience_descriptions(st.session_state.experiences),
                        "activities": enhance_activity_descriptions(st.session_state.activities)
                    }
                    
                    # List of themes
                    resume_data = sanitize_resume_data(resume_data)
                    themes = ["sb2nov", "moderncv", "classic", "engineeringresumes"]
                    
                    # Generate and save YAML for each theme
                    saved_files = []
                    for theme in themes:
                        yaml_content = generate_resume_yaml(resume_data, theme)
                        filename = save_resume_yaml(yaml_content, name, theme, timestamp)
                        saved_files.append(filename)

                    # Save YAML files to session state
                    st.session_state.saved_yaml_files = saved_files

                    # Create and run the render script
                    try:
                        script_name, output_dir = create_render_script(name, timestamp)
                        success, script_output = run_render_script(script_name)
                        
                        if success:
                            # Save output directory to session state
                            st.session_state.output_dir = output_dir
                            
                            # Get and save PDF files to session state
                            pdf_files = [f for f in os.listdir(output_dir) if f.endswith('.pdf')]
                            st.session_state.generated_files = pdf_files
                            
                            # Display success message
                            st.success("Resume generation complete!")
                        else:
                            st.error("Failed to generate PDFs. Error message:")
                            st.code(script_output)
                            
                    except Exception as e:
                        st.error(f"Error during PDF generation: {str(e)}")
                
                except Exception as e:
                    st.error(f"An error occurred during resume generation: {str(e)}")

    # Display generated files information (outside the generate button)
    if st.session_state.saved_yaml_files:
        st.write("Generated YAML files (saved in 'yamlfiles' directory):")
        for file in st.session_state.saved_yaml_files:
            st.write(f"- {file}")

    if st.session_state.output_dir and st.session_state.generated_files:
        st.write(f"\nPDF files have been generated and are available in:")
        st.code(st.session_state.output_dir)
        
        st.write("\nYou can download your PDFs here:")
        for pdf_file in st.session_state.generated_files:
            try:
                with open(os.path.join(st.session_state.output_dir, pdf_file), 'rb') as f:
                    pdf_data = f.read()
                    st.download_button(
                        label=f"Download {pdf_file}",
                        data=pdf_data,
                        file_name=pdf_file,
                        mime='application/pdf',
                        key=f"download_{pdf_file}"  # Unique key for each button
                    )
            except Exception as e:
                st.warning(f"Unable to create download button for {pdf_file}: {str(e)}")

if __name__ == "__main__":
    main()
