# app.py

from flask import Flask, request, jsonify
import time
import random
import os
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

# Initialize Airtable client
airtable_client = AirtableClient()

def read_last_processed_time():
    """
    Read the last processed time from 'last_processed_time.txt'
    """
    if os.path.exists('last_processed_time.txt'):
        with open('last_processed_time.txt', 'r') as file:
            last_time = file.read().strip()
            if last_time:
                return last_time
    # If the file doesn't exist or is empty, return a default past date
    return '2024-11-05T00:00:00.000Z'

def write_last_processed_time(last_time):
    """
    Write the last processed time to 'last_processed_time.txt'
    """
    with open('last_processed_time.txt', 'w') as file:
        file.write(last_time)

def process_generation_request(request):
    # Extract request details
    request_id = request['id']
    fields = request['fields']
    user_id = fields.get('Accounts (Users)')[0]
    content_format = fields.get('Type')
    amount_to_generate = int(fields.get('Amount To Generate', 1))
    source_ids = fields.get("Source_ID (from Source to Generate From?)")
    template_tags = fields.get('Template Tag To Use', [])
    category = fields.get('Select 2')

    # Fetch user data
    user = airtable_client.get_user_by_id(user_id)
    brand_voice = user['fields'].get('Brand Voice', '')
    sample_content = airtable_client.get_sample_content(user)

    generated_count = 0
    attempts = 0
    max_attempts = amount_to_generate * 5  # Limit to prevent infinite loops

    while generated_count < amount_to_generate and attempts < max_attempts:
        attempts += 1
        print(f"Generating content {generated_count + 1}/{amount_to_generate}")

        # Get a random QA pair
        qa_pair = airtable_client.get_random_qa_pair(source_ids)
        if not qa_pair:
            print("No QA pairs available.")
            break
        question = qa_pair['fields'].get('Question', '')
        answer = qa_pair['fields'].get('Answer', '')

        # Get a random template
        templates = airtable_client.get_templates(content_format, template_tags, category)
        if not templates:
            print("No templates available.")
            break
        template = random.choice(templates)['fields'].get('Template', '')

        # Generate content
        prompt = generate_content_prompt(brand_voice)
        content = generate_content_with_claude(prompt, question, answer, template)
        content = voice_and_brand_edit_with_claude(prompt, question, answer, template, content, brand_voice)

        # Ensure content is within character limit
        if len(content) > 280:
            content = rewrite_content_to_fit_limit(content)

        print(content)

        # AI screening
        screening_result = ai_screen_content(content, sample_content)
        print(screening_result)

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
        airtable_client.save_generated_content({
            'Generation Request': [request_id],
            'First draft': content,
            'AI screen': content_status,
            'Screening Result': screening_result
        })

        if approved:
            generated_count += 1
        else:
            print("Content rejected by AI screener.")

        # Delay to respect API rate limits
        time.sleep(1)

        print([request_id])
        print(content_status)
        print("----------------------")

def check_for_new_requests():
    print("Checking for new generation requests...")
    last_processed_time = read_last_processed_time()
    generation_requests = airtable_client.get_new_generation_requests(last_processed_time)
    if generation_requests:
        # Sort requests by 'Created Time' to process them in order
        generation_requests.sort(key=lambda x: x['createdTime'])
        for request in generation_requests:
            print(f"Processing generation request ID: {request['id']}")
            process_generation_request(request)
            # Update the last processed time
            last_processed_time = request['createdTime']
            write_last_processed_time(last_processed_time)
    else:
        print("No new generation requests found.")

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
