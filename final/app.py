# app.py

from flask import Flask, request, jsonify
import time
import random
import os
from pathlib import Path
import logging
from airtable_utils import AirtableClient
from ai_utils import (
    generate_content_with_claude,
    voice_and_brand_edit_with_claude,
    rewrite_content_to_fit_limit,
    ai_screen_content,
    generate_content_prompt,
)
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize Airtable client
airtable_client = AirtableClient()

def read_last_processed_time():
    """
    Read the last processed time from 'last_processed_time.txt' in the current directory
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'last_processed_time.txt')
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                last_time = file.read().strip()
                if last_time:
                    return last_time
    except Exception as e:
        logging.error(f"Error reading last_processed_time.txt: {e}")
    # If the file doesn't exist or is empty, return a default past date
    return '2024-11-05T00:00:00.000Z'

def write_last_processed_time(last_time):
    """
    Write the last processed time to 'last_processed_time.txt'
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'last_processed_time.txt')
    try:
        with open(file_path, 'w') as file:
            file.write(last_time)
    except Exception as e:
        logging.error(f"Error writing to last_processed_time.txt: {e}")

def process_generation_request(request):
    try:
        # Extract request details
        request_id = request['id']
        fields = request['fields']
        user_ids = fields.get('Accounts (Users)', [])
        if not user_ids:
            logging.warning(f"No user ID found for request ID: {request_id}")
            return
        user_id = user_ids[0]
        content_format = fields.get('Type')
        amount_to_generate = int(fields.get('Amount To Generate', 1))
        source_ids = fields.get("Source_ID (from Source to Generate From?)", [])
        template_tags = fields.get('Template Tag To Use', [])
        category = fields.get('Select 2')

        # Fetch user data
        user = airtable_client.get_user_by_id(user_id)
        if not user:
            logging.error(f"User with ID {user_id} not found.")
            return
        brand_voice = user['fields'].get('Brand Voice', '')
        sample_content = airtable_client.get_sample_content(user)

        generated_count = 0
        attempts = 0
        max_attempts = amount_to_generate * 5  # Limit to prevent infinite loops

        while generated_count < amount_to_generate and attempts < max_attempts:
            attempts += 1
            logging.info(f"Generating content {generated_count + 1}/{amount_to_generate}")

            # Get a random QA pair
            qa_pair = airtable_client.get_random_qa_pair(source_ids)
            if not qa_pair:
                logging.warning("No QA pairs available.")
                break
            question = qa_pair['fields'].get('Question', '')
            answer = qa_pair['fields'].get('Answer', '')

            # Get a random template
            templates = airtable_client.get_templates(content_format, template_tags, category)
            if not templates:
                logging.warning("No templates available.")
                break
            template = random.choice(templates)['fields'].get('Template', '')

            # Generate content
            prompt = generate_content_prompt(brand_voice)
            try:
                content = generate_content_with_claude(prompt, question, answer, template)
                content = voice_and_brand_edit_with_claude(prompt, question, answer, template, content, brand_voice)
            except Exception as e:
                logging.error(f"Error during content generation with Claude: {e}")
                continue

            # Ensure content is within character limit
            if len(content) > 280:
                try:
                    content = rewrite_content_to_fit_limit(content)
                except Exception as e:
                    logging.error(f"Error during content rewriting to fit limit: {e}")
                    continue

            logging.info(f"Generated Content: {content}")

            # AI screening
            try:
                screening_result = ai_screen_content(content, sample_content)
            except Exception as e:
                logging.error(f"Error during AI screening: {e}")
                continue

            logging.info(f"Screening Result: {screening_result}")

            # Parse screening result
            approved = False
            lines = screening_result.strip().splitlines()
            if lines:
                first_line = lines[0].strip().lower()
                if 'yes' in first_line:
                    approved = True
                elif 'no' in first_line:
                    approved = False
            content_status = 'Approved' if approved else 'Rejected'

            # Save generated content
            try:
                airtable_client.save_generated_content({
                    'Generation Request': [request_id],
                    'First draft': content,
                    'AI screen': content_status,
                    'Screening Result': screening_result
                })
            except Exception as e:
                logging.error(f"Error saving generated content to Airtable: {e}")
                continue

            if approved:
                generated_count += 1
            else:
                logging.info("Content rejected by AI screener.")

            # Delay to respect API rate limits
            time.sleep(1)

            logging.info(f"Processed Request ID: {request_id}, Status: {content_status}")
            logging.info("----------------------")
    except Exception as e:
        logging.error(f"Error processing generation request: {e}")

def check_for_new_requests():
    try:
        logging.info("Checking for new generation requests...")
        last_processed_time = read_last_processed_time()
        print(last_processed_time)
        generation_requests = airtable_client.get_new_generation_requests(last_processed_time)
        if generation_requests:
            # Sort requests by 'Created Time' to process them in order
            generation_requests.sort(key=lambda x: x['createdTime'])
            for request in generation_requests:
                logging.info(f"Processing generation request ID: {request['id']}")
                process_generation_request(request)
                # Update the last processed time
                last_processed_time = request['createdTime']
                write_last_processed_time(last_processed_time)
        else:
            logging.info("No new generation requests found.")
    except Exception as e:
        logging.error(f"Error in check_for_new_requests: {e}")

# Set up the scheduler to run check_for_new_requests() every 30 seconds
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_for_new_requests, trigger="interval", seconds=30)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

# Define a simple route to ensure the app is running
@app.route('/')
def index():
    return "Ghostwriter Automation Web App is running."

if __name__ == "__main__":
    # Run the Flask app
    app.run(host='0.0.0.0', port=8080)
