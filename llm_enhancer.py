import boto3
import json
from io import BytesIO
import PyPDF2
import re

def get_rag_data_from_pdf():
    s3 = boto3.client('s3')
    bucket_name = 'resume-builder-mockup-bucket'
    keys = ['Federal Resume Samples.pdf', 'sample-resume.pdf']
    combined_text = ''

    for key in keys:
        try:
            response = s3.get_object(Bucket=bucket_name, Key=key)
            pdf_content = response['Body'].read()
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text()
            combined_text += text + '\n'
        except Exception as e:
            print(f"Error fetching or parsing PDF from S3 for {key}: {e}")
            continue
    
    return combined_text

def clean_bullet_points(text):
    """
    Remove leading bullet point markers while preserving proper spacing and formatting.
    Includes multiple cleaning passes to ensure all bullet points are removed.
    
    Args:
        text (str): Text containing bullet points
    
    Returns:
        str: Cleaned text with bullet points removed but spacing preserved
    """
    # Split into lines but preserve original whitespace
    lines = text.splitlines()
    cleaned_lines = []
    
    for line in lines:
        # Skip completely empty lines
        if not line:
            continue
            
        # Remove bullet points but preserve any indentation
        # First capture any leading whitespace
        leading_space = re.match(r'^(\s*)', line).group(1)
        
        # First pass: Remove common bullet point patterns while preserving whitespace
        line = re.sub(r'^(\s*)[•\*\-]\s+|\d+\.\s+', leading_space, line)
        
        # Second pass: Remove any remaining bullet points or symbols at the start
        # This catches any bullets that might have slipped through
        line = re.sub(r'^(\s*)(?:[•\*\-‣⁃◦→▪️●■]+\s*)+', r'\1', line)
        
        # Third pass: Clean up any bullet points that might appear mid-line
        # This is a safety check in case the model includes bullets in unexpected places
        line = re.sub(r'[•\*\-‣⁃◦→▪️●■]\s+', '', line)
        
        # Ensure first letter of actual content is capitalized
        content_match = re.match(r'^(\s*)(.+)$', line)
        if content_match:
            spaces, content = content_match.groups()
            # Only proceed if we have actual content
            if content.strip():
                line = spaces + content[0].upper() + content[1:] if len(content) > 1 else content.upper()
            
        # Ensure line ends with a period if it's not empty
        if line.strip() and not line.strip().endswith('.'):
            line += '.'
            
        cleaned_lines.append(line)
    
    # Join lines back together with original line endings
    result = '\n'.join(cleaned_lines)
    
    # Final safety check: one more pass over the entire text to catch any remaining bullets
    result = re.sub(r'[•\*\-‣⁃◦→▪️●■]\s*', '', result)
    
    return result

def create_prompt(experience):
    rag_data = get_rag_data_from_pdf()
    prompt = f"""
Human:
You are a career advisor who is focused on helping students (high school or college) or recently graduated students improve their resumes.
Here's a good bit of information about resumes generally speaking and a few good examples of how resumes should read {rag_data}

Based on the following information provided under 'Work Experience:', generate the new 'Experience' section of the student's professional resume. Reword and enhance upon the details to make them more compelling and suitable for inclusion in a professional resume.

Guidelines:

**Format Requirements:**

- **Important:** Do not use special symbols and characters because they can cause issues within the resume renderer.
- Please format the output as follows:

### Experience ###
(Enhanced experience content here)

- Do not have any comments/notes after the enhanced experience content.
- Finish any generated bullet points with a period.
- Do not add any extra empty lines between the generated bullet points. Simply one newline between the bullet points to ensure they are on separate lines.

**Content Requirements:**

- Do not include any personal information like name, contact details, or education.
- Do not include any new numbers and percentages in terms of impact. The only quantification of impact should be whatever the user literally states.
- Do not create new sentences, independent/dependent clauses, or bullet points; rather improve what is already there.
- Always err on the side of caution to not add new bullet points and experiences that the user did not previously state.
- Be articulate and succinct and do not use excessive jargon to fill in.
- When necessary, fix grammatical errors that the user made inside of the work experience.
- Your goal with this is to simply express what the user has done, rather than impress readers.
- The potential reader is expected to have some level of technical expertise in the field, so do not overexplain or restate the obvious. For example, rather than saying the X programming language or Y framework, you can just say the language or framework in question.

Work Experience:
{experience}
Assistant:
"""
    return prompt
def generate_experience(prompt):
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    try:
        request_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 50000,
            "temperature": 0.2,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
        response = bedrock.invoke_model(
            modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
            contentType='application/json',
            accept='application/json',
            body=request_body
        )
        response_body = json.loads(response['body'].read())
        content = response_body.get('content', [])
        if content and isinstance(content, list) and 'text' in content[0]:
            return content[0]['text']
        else:
            print("Unexpected response format from the model.")
            return ""
    except Exception as e:
        print(f"An error occurred while invoking the model: {e}")
        return ""


def generate_enhanced_experience(experience):
    prompt = create_prompt(experience)
    generated_text = generate_experience(prompt)
    parsed_experience = parse_experience(generated_text)
    return parsed_experience

def create_bio_prompt(bio):
    rag_data = get_rag_data_from_pdf()
    prompt = f"""
Human:
You are a career advisor specializing in federal resumes, focusing on helping applicants create compelling professional summaries that align with federal resume standards.
Here's reference information about federal resumes and examples of effective professional summaries: {rag_data}

Based on the following information provided under 'Professional Summary:', generate an enhanced professional summary section suitable for a federal resume. Reword and improve the content while maintaining accuracy and federal resume formatting standards.

Guidelines:

**Format Requirements:**

- **Important:** Do not use special symbols and characters because they can cause issues within the resume renderer.
- Please format the output as follows:

### Professional Summary ###
(Enhanced professional summary here)

- Do not have any comments/notes after the enhanced professional summary content.
- Format as a cohesive paragraph rather than bullet points.
- End sentences with proper punctuation.
- Maintain a formal, professional tone appropriate for federal positions.

**Content Requirements:**

- Do not include any personal information like name, contact details, or education.
- Do not include any new numbers and percentages in terms of impact; the only quantification of impact should be whatever the user literally states.
- Do not create new sentences, independent/dependent clauses, or bullet points; rather improve what is already there.
- Always err on the side of caution to not add new bullet points and experiences that the user did not previously state.
- Be articulate and succinct and do not use excessive jargon to fill in.
- When necessary, fix grammatical errors that the user made in the professional summary.
- Your goal with this is to simply express what the user has done, rather than impress readers.
- The potential reader is expected to have some level of technical expertise in the field, so do not overexplain or restate the obvious. For example, rather than saying the X programming language or Y framework, you can just say the language or framework in question.
- Do not add new achievements or qualifications not mentioned in the original.

Professional Summary:
{bio}
Assistant:
"""
    return prompt

def generate_bio(prompt):
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    try:
        request_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 50000,
            "temperature": 0.2,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
        response = bedrock.invoke_model(
            modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
            contentType='application/json',
            accept='application/json',
            body=request_body
        )
        response_body = json.loads(response['body'].read())
        content = response_body.get('content', [])
        if content and isinstance(content, list) and 'text' in content[0]:
            return content[0]['text']
        else:
            print("Unexpected response format from the model.")
            return ""
    except Exception as e:
        print(f"An error occurred while invoking the model: {e}")
        return ""

def generate_enhanced_bio(bio):
    prompt = create_bio_prompt(bio)
    generated_text = generate_bio(prompt)
    parsed_bio = parse_bio(generated_text)
    return parsed_bio


def create_activity_prompt(activity):
    rag_data = get_rag_data_from_pdf()
    prompt = f"""
Human:
You are a career advisor who specializes in helping students enhance their extracurricular activities and leadership experiences for resumes and applications.
Here's reference information about effective descriptions and examples: {rag_data}

Based on the following information provided under 'Activities:', generate enhanced activity descriptions that highlight leadership, initiative, and impact while maintaining accuracy. Each activity should be compelling and suitable for a professional resume.

Guidelines:

**Format Requirements:**

- **Important:** Do not use special symbols and characters because they can cause issues within the resume renderer.
- Please format the output as follows:

### Activities ###
(Enhanced activities content here)

- Do not have any comments/notes after the enhanced activities content.
- Each activity description MUST be formatted as a bullet point starting with "- ".
- Each bullet point MUST be on its own line.
- Each bullet point MUST end with a period.
- Do not add empty lines between bullet points.
- Do not format as paragraphs—each item must be a separate bullet point.

**Content Requirements:**

- Do not include any personal information like name, contact details, or education.
- Do not include any new numbers and percentages in terms of impact; only use quantification that the user literally states.
- Do not create new activities or bullet points; only enhance what is already provided.
- Be articulate and succinct; avoid excessive jargon.
- Fix any grammatical errors in the original text.
- Use strong action verbs at the start of each bullet point.
- Focus on leadership, initiative, and impact when present in the original text.
- Keep technical terms concise (e.g., use "Python" instead of "Python programming language").
- Maintain a professional tone throughout.

Activities:
{activity}
Assistant:
"""
    return prompt

def generate_activity(prompt):
    bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
    try:
        request_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 50000,
            "temperature": 0.2,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
        response = bedrock.invoke_model(
            modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
            contentType='application/json',
            accept='application/json',
            body=request_body
        )
        response_body = json.loads(response['body'].read())
        content = response_body.get('content', [])
        if content and isinstance(content, list) and 'text' in content[0]:
            return content[0]['text']
        else:
            print("Unexpected response format from the model.")
            return ""
    except Exception as e:
        print(f"An error occurred while invoking the model: {e}")
        return ""

def parse_experience(experience_text):
    """
    Parse and clean experience text while preserving formatting.
    
    Args:
        experience_text (str): Raw experience text from model
        
    Returns:
        str: Cleaned and properly formatted experience text
    """
    lines = experience_text.splitlines()
    experience_content = []
    start_parsing = False
    
    for line in lines:
        if line.strip() == "### Experience ###":
            start_parsing = True
            continue
        elif start_parsing:
            experience_content.append(line)
    
    # Join with newlines before cleaning to preserve original formatting
    full_content = '\n'.join(experience_content)
    cleaned_content = clean_bullet_points(full_content)
    return cleaned_content.strip()  # Only strip at the very end

def parse_bio(bio_text):
    lines = bio_text.splitlines()
    bio_content = ''
    start_parsing = False
    for line in lines:
        line = line.strip()
        if line == "### Professional Summary ###":
            start_parsing = True
            continue
        elif start_parsing:
            bio_content += line + ' '
    return bio_content.strip()


def parse_activity(activity_text):
    """
    Parse and clean activity text while preserving formatting.
    
    Args:
        activity_text (str): Raw activity text from model
        
    Returns:
        str: Cleaned and properly formatted activity text
    """
    lines = activity_text.splitlines()
    activity_content = []
    start_parsing = False
    
    for line in lines:
        if line.strip() == "### Activities ###":
            start_parsing = True
            continue
        elif start_parsing:
            activity_content.append(line)
    
    # Join with newlines before cleaning to preserve original formatting
    full_content = '\n'.join(activity_content)
    cleaned_content = clean_bullet_points(full_content)
    return cleaned_content.strip()  # Only strip at the very end

def generate_enhanced_activity(activity):
    prompt = create_activity_prompt(activity)
    generated_text = generate_activity(prompt)
    parsed_activity = parse_activity(generated_text)
    return parsed_activity

if __name__ == "__main__":
    user_experience = """
• •Led development team of eight engineers in delivering enterprise software solu-
tions.
• •Implemented Agile methodologies, resulting in faster project delivery.
• •Managed million-dollar budget while maintaining project scope and deadlines.
• •Developed and maintained client relationships across multiple major accounts.
• •Introducedautomatedtestingframework,reducingbugreports.
    """
    enhanced_experience = generate_enhanced_experience(user_experience)
    print("Enhanced Experience Section:")
    print(enhanced_experience)


    user_bio = """
    Dedicated professional with a background in software development and project management. Experienced in leading cross-functional teams and delivering high-impact solutions. Strong focus on continuous learning and innovation.
    """
    enhanced_bio = generate_enhanced_bio(user_bio)
    print("Enhanced Professional Summary:")
    print(enhanced_bio)


    user_activity = """
    Led student coding club meetings
    Helped organize hackathon event
    Participated in robotics competition
    """
    enhanced_activity = generate_enhanced_activity(user_activity)
    print("\nEnhanced Activity Section:")
    print(enhanced_activity)
